# SPDX-License-Identifier: MIT

from BM869S import BM869S
from time import sleep, perf_counter
import paho.mqtt.client as mqtt
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from urllib.parse import urlparse
import logging
import math

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_ignore_empty=True
    )
    mqtt_uri: str = Field(pattern=r"^(mqtt|mqtts)://[a-zA-Z0-9\.\-]+(:[0-9]+)$")
    mqtt_user: str = ""
    mqtt_pass: str = ""
    mqtt_topic: str
    mqtt_line_proto_measurement: str
    mqtt_send_interval: int = 10  # seconds
    mqtt_ca_cert: str = ""  # path to CA certificate for MQTT over TLS


def on_connect(mqttc, obj, flags, reason_code, properties):
    print("connect reason_code: " + str(reason_code))


def connect_uri(client: mqtt.Client, settings: Settings):
    uri = urlparse(settings.mqtt_uri)
    default_port = 1883

    if uri.scheme == "mqtts":
        if not settings.mqtt_ca_cert or settings.mqtt_ca_cert == "":
            client.tls_set()
        elif settings.mqtt_ca_cert == "skip":
            client.tls_set(cert_reqs=mqtt.ssl.CERT_NONE)
        else:
            client.tls_set(ca_certs=settings.mqtt_ca_cert)
        default_port = 8883

    if settings.mqtt_user and settings.mqtt_pass:
        client.username_pw_set(settings.mqtt_user, settings.mqtt_pass)
        print(
            f"connecting to {uri.hostname}:{uri.port or default_port} with user {settings.mqtt_user}"
        )
    else:
        print(f"connecting to {uri.hostname}:{uri.port or default_port} as anonymous")

    client.connect(uri.hostname, uri.port or default_port, 10)
    client.loop_start()


def is_number(s):
    try:
        num = float(s)
        return math.isfinite(num)
    except ValueError:
        return False


def main():
    while True:
        try:
            BM = BM869S()
            PRI_READING = 0
            PRI_UNIT = 1
            SEC_READING = 2
            SEC_UNIT = 3

            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, reconnect_on_failure=True
            )
            client.enable_logger(logger)
            client.on_connect = on_connect
            settings = Settings()
            connect_uri(client, settings)

            start = perf_counter()
            now = perf_counter() - start
            while True:
                now = perf_counter() - start
                value = BM.readdata()
                msg = f"{settings.mqtt_line_proto_measurement} "

                if is_number(value[PRI_READING]):  # overload values will be ignored
                    msg += f'MES1={float(value[PRI_READING])},UNIT1="{value[PRI_UNIT]}"'

                if is_number(value[SEC_READING]):
                    msg += (
                        f',MES2={float(value[SEC_READING])},UNIT2="{value[SEC_UNIT]}"'
                    )

                if msg != f"{settings.mqtt_line_proto_measurement} ":
                    ret = client.publish(settings.mqtt_topic, msg)
                    if ret.rc == mqtt.MQTT_ERR_SUCCESS:
                        logger.info(f"PUB: {msg}")
                    else:
                        logger.warning(f"Failed to publish message: {ret.rc}")

                elapsed = (perf_counter() - start) - now
                if elapsed < settings.mqtt_send_interval:
                    sleep(settings.mqtt_send_interval - elapsed)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.warning(e)
            logger.info("retrying connection")
            sleep(5)
            continue


if __name__ == "__main__":
    main()
