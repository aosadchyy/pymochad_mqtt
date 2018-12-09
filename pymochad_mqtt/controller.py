# Copyright 2018 Alex Osadchyy
#
# This file is part of pymochad_mqtt
# https://github.com/aosadchyy/pymochad_mqtt

import logging
import time
import threading
from pymochad import controller
from pymochad_mqtt import parser
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import json

_LOGGER = logging.getLogger(__name__)


class PyMochadMqtt(threading.Thread):
    """PyMochadMqtt controller class
    Mochad daemon wrapper in Python with mqtt interface for a simplified send and 
    receive of X10 messages. Required mochad and mqtt services running to connect them.
    
    :param str mochad_server: Host running mochad daemon. Defaults to localhost.
    :param int mochad_port: Port to which mochad is binding.Default port is 1099.
    :param str mqtt_broker: Host running mqtt broker. Defaults to localhost.
    :param int mqtt_port: Port to which mqtt is binding.Default port is 1883.
    :param dict mqtt_auth: authentication parameters for the mqtt client
                       {'username':"<username>", 'password':"<password>"}
    """
    def __init__(self, mochad_server='localhost', mochad_port=1099, 
                 mqtt_broker='localhost', mqtt_port=1883, mqtt_auth=None):
        self._mochad_server=mochad_server
        self._mochad_port=mochad_port
        self._mqtt_broker=mqtt_broker
        self._mqtt_port=mqtt_port
        self._mqtt_auth=mqtt_auth
        self.parser=parser.X10Parser()
        self.connect_event = threading.Event()

        super().__init__()

    def run(self):
        self.ctrl = controller.PyMochad(server=self._mochad_server, port=self._mochad_port)      
        self.connect_event.set()
        self._ws_listen()

    def _ws_listen(self):
        _LOGGER.info("Entering Mochad event listening loop")
        try:
            # READ FROM NETWORK LOOP
            retry_count = 0
            while True:
                try:
                    content = self.ctrl.read_data()
                except Exception as e:
                    _LOGGER.error(
                        "Failed to read from the socket. %s", str(e))
                    if retry_count >= 300:
                        raise Exception(
                            "Retry attempts exceeded. Failed to read for the"
                            " socket.")
                    else:
                        retry_count += 1
                    time.sleep(10)
                    content = ""
                # an empty string means connection lost, skip the loop
                if content:
                    retry_count = 0
                    for line in content.splitlines():
                        _LOGGER.debug("Line received: %s", line)
                        """ Examples of single and multi-lines received
                            10/14 15:02:01 Unknown RF camera command
                            10/14 15:02:01 5D 14 4F 4C A0
                            10/14 15:02:01 Invalid checksum 0x2B
                            10/14 15:02:01 5D 20 20 0B F4 CA
                            10/14 15:02:07 Rx RF HouseUnit: A8 Func: On
                            10/14 15:03:01 Rx RFSEC Addr: 5F:65:00 Func: Contact
                                                    _normal_max_low_DS10A
                        """
                        try:
                            addr, message_dict, kind = self.parser.parse_mochad_line(
                                  line.rstrip())
                        except Exception as e:
                            _LOGGER.debug(
                                  "Failed to parse mochad msg %s:%s", line, str(e))
                            continue
            
                        # addr/func are blank when nothing to dispatch
                        if addr and message_dict:
                            _LOGGER.debug(
                                "Future callback %s:%s", addr, 
                                                               message_dict)
                            self._process_message(addr, message_dict, kind)
                else:
                    # this section shoudl never be reached. 
                    # read_data() is blocking inside
                    time.sleep(1)
                    continue 
        except Exception as e:
            _LOGGER.error("Failed to read from the socket. %s", str(e))
        finally:
            _LOGGER.error("Loop exited. No more X10 msgs will be received.")
            if self.ctrl.socket:
                self.disconnect()

    def _process_message(self, addr, message_dict, kind):
        """
        Publish, in json format, a dict to an MQTT broker
        """
        topic = "X10/{}/{}".format(
              kind, addr)
        payload = json.dumps(message_dict)
        
        if kind == 'button':
            value=message_dict['func']
        else:
            value=message_dict['event_state']
        _LOGGER.warning("Publish %s : %s to mqtt", topic, value)
        self._publish(topic, payload)
        # mimic a pulsing nature of a sensor. set to off after on
        if value == 'on':
            _LOGGER.debug("Publish %s : off to mqtt", topic)
            self._publish(topic, payload.replace("on","off"))

    def _publish(self, topic, payload):
            try:
                publish.single(topic, payload=payload, qos=0, retain=False, hostname=self._mqtt_broker,
                    port=self._mqtt_port, client_id="", keepalive=15, will=None, auth=self._mqtt_auth, tls=None,
                    protocol=mqtt.MQTTv311, transport="tcp")
            except Exception as e:
                _LOGGER.error("Failed to publish mqtt message %s:%s. %s", topic, payload, str(e))
    
    def disconnect(self):
        """Close the connection to the mochad socket."""
        self.ctrl.socket.close()
