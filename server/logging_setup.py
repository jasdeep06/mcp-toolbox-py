
import coloredlogs, logging, socket, sys, time

HOSTNAME = socket.gethostname()

class HostnameFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.hostname = HOSTNAME
        return True

LOG_FMT = (
    "%(asctime)s %(hostname)s %(levelname)-8s "
    "%(name)s: %(message)s"
)
DATE_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"

root = logging.getLogger()
root.setLevel(logging.INFO)
root.handlers.clear()                       # ditch default basicConfig

handler = logging.StreamHandler(sys.stdout)
handler.addFilter(HostnameFilter())
coloredlogs.install(
    logger=root,
    level="INFO",
    stream=sys.stdout,
    fmt=LOG_FMT,
    datefmt=DATE_FMT,
    milliseconds=True,       # show .123 part
    field_styles=dict(levelname=dict(bold=True)),
    level_styles=dict(
        info=dict(color="green"),
        warning=dict(color="yellow"),
        error=dict(color="red"),
        critical=dict(color="red", background="white"),
    ),
)
