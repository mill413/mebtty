import ctypes
import ctypes.util
import os
import pwd
from dataclasses import dataclass

from app.config import settings


NON_INTERACTIVE_SHELLS = {
    "false",
    "nologin",
    "sync",
    "shutdown",
    "halt",
}


@dataclass(frozen=True)
class LocalUser:
    username: str
    uid: int
    gid: int
    home: str
    shell: str


def _is_interactive_user(entry: pwd.struct_passwd) -> bool:
    shell_name = os.path.basename(entry.pw_shell or "")
    if shell_name in NON_INTERACTIVE_SHELLS:
        return False
    if entry.pw_uid == 0 and not settings.ALLOW_ROOT_LOCAL_USER:
        return False
    return bool(entry.pw_name and entry.pw_dir and entry.pw_shell)


def _entry_to_local_user(entry: pwd.struct_passwd) -> LocalUser:
    return LocalUser(
        username=entry.pw_name,
        uid=entry.pw_uid,
        gid=entry.pw_gid,
        home=entry.pw_dir,
        shell=entry.pw_shell or "/bin/sh",
    )


def resolve_local_user(username: str | None) -> LocalUser:
    if not username:
        raise ValueError("Local username is required")

    try:
        entry = pwd.getpwnam(username)
    except KeyError as exc:
        raise ValueError(f"Local user '{username}' does not exist") from exc
    if not _is_interactive_user(entry):
        if entry.pw_uid == 0 and not settings.ALLOW_ROOT_LOCAL_USER:
            raise ValueError("Root local user is disabled")
        raise ValueError(
            f"Local user '{username}' is not available for terminal sessions"
        )
    return _entry_to_local_user(entry)


class _PamMessage(ctypes.Structure):
    _fields_ = [
        ("msg_style", ctypes.c_int),
        ("msg", ctypes.c_char_p),
    ]


class _PamResponse(ctypes.Structure):
    _fields_ = [
        ("resp", ctypes.c_void_p),
        ("resp_retcode", ctypes.c_int),
    ]


_PAM_SUCCESS = 0
_PAM_PROMPT_ECHO_OFF = 1
_PAM_PROMPT_ECHO_ON = 2
_PAM_ERROR_MSG = 3
_PAM_TEXT_INFO = 4
_PAM_CONV_ERR = 19
_PAM_AUTH_ERR = 7


def _load_pam() -> tuple[ctypes.CDLL, ctypes.CDLL]:
    pam_path = ctypes.util.find_library("pam")
    if not pam_path:
        raise RuntimeError("PAM library is not available on this system")
    libc_path = ctypes.util.find_library("c")
    if not libc_path:
        raise RuntimeError("C runtime library is not available on this system")

    pam = ctypes.CDLL(pam_path)
    libc = ctypes.CDLL(libc_path)
    return pam, libc


def authenticate_local_user(username: str, password: str) -> bool:
    password_bytes = password.encode("utf-8")
    service = (settings.PAM_SERVICE or "login").encode("utf-8")
    pam, libc = _load_pam()

    libc.calloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
    libc.calloc.restype = ctypes.c_void_p
    libc.strdup.argtypes = [ctypes.c_char_p]
    libc.strdup.restype = ctypes.c_void_p

    conversation_callback_type = ctypes.CFUNCTYPE(
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.POINTER(_PamMessage)),
        ctypes.POINTER(ctypes.POINTER(_PamResponse)),
        ctypes.c_void_p,
    )

    @conversation_callback_type
    def conversation(num_msg, messages, responses, appdata_ptr):
        response_size = ctypes.sizeof(_PamResponse)
        response_memory = libc.calloc(num_msg, response_size)
        if not response_memory:
            return _PAM_CONV_ERR

        response_array = ctypes.cast(
            response_memory,
            ctypes.POINTER(_PamResponse),
        )
        for index in range(num_msg):
            style = messages[index].contents.msg_style
            if style in (_PAM_PROMPT_ECHO_OFF, _PAM_PROMPT_ECHO_ON):
                duplicated = libc.strdup(password_bytes)
                if not duplicated:
                    return _PAM_CONV_ERR
                response_array[index].resp = duplicated
                response_array[index].resp_retcode = 0
            elif style in (_PAM_ERROR_MSG, _PAM_TEXT_INFO):
                response_array[index].resp = None
                response_array[index].resp_retcode = 0
            else:
                return _PAM_CONV_ERR

        responses[0] = response_array
        return _PAM_SUCCESS

    class PamConv(ctypes.Structure):
        _fields_ = [
            ("conv", conversation_callback_type),
            ("appdata_ptr", ctypes.c_void_p),
        ]

    pam.pam_start.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.POINTER(PamConv),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    pam.pam_start.restype = ctypes.c_int
    pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_authenticate.restype = ctypes.c_int
    pam.pam_acct_mgmt.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_acct_mgmt.restype = ctypes.c_int
    pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_end.restype = ctypes.c_int

    handle = ctypes.c_void_p()
    pam_conv = PamConv(conversation, None)

    status = pam.pam_start(
        service,
        username.encode("utf-8"),
        ctypes.byref(pam_conv),
        ctypes.byref(handle),
    )
    if status == _PAM_SUCCESS:
        status = pam.pam_authenticate(handle, 0)
    if status == _PAM_SUCCESS:
        status = pam.pam_acct_mgmt(handle, 0)
    if handle.value:
        pam.pam_end(handle, status)

    if status == _PAM_SUCCESS:
        return True
    if status == _PAM_AUTH_ERR:
        return False
    return False
