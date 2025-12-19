from typing import ClassVar, Final, Mapping, Optional, Sequence, Tuple

from typing_extensions import Self
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.services.generic import *
from viam.utils import ValueTypes
from smbus2 import SMBus
import json
import io

MESSAGE_CHUNK_SIZE = 128


def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i : i + n]

class MultiLed(Generic, EasyResource):
    # To enable debug-level logging, either run viam-server with the --debug option,
    # or configure your resource/machine to display debug logs.
    MODEL: ClassVar[Model] = Model(
        ModelFamily("vijayvuyyuru", "multi-led"), "multi-led"
    )
    bus = None
    strand_length = 0
    num_strands = 0
    brightness = 0
    address = 0

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this Generic service.
        The default implementation sets the name from the `config` parameter.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both required and optional)

        Returns:
            Self: The resource
        """
        self = super().new(config, dependencies)
        num_strands: int = int(config.attributes.fields["num_strands"].number_value)
        strand_length: int = int(config.attributes.fields["strand_length"].number_value)
        brightness: float = config.attributes.fields["brightness"].number_value
        address_hex_string = config.attributes.fields["address"].string_value
        self.logger.info(f"address hex string: {address_hex_string}")
        address = int(address_hex_string, 16)
        self.logger.info(f"converted address: {address}")

        if self.bus is not None:
            self.bus.close()

        self.bus = SMBus(1)
        pixel_config = {
            "reconfigure": {
                "num_strands": num_strands,
                "strand_length": strand_length,
                "brightness": brightness,
            }
        }
        self.num_strands = num_strands
        self.strand_length = self.strand_length
        self.brightness = brightness
        self.address = address

        self.send_message(pixel_config)


        return super().new(config, dependencies)

    @classmethod
    def validate_config(
        cls, config: ComponentConfig
    ) -> Tuple[Sequence[str], Sequence[str]]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any required dependencies or optional dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Tuple[Sequence[str], Sequence[str]]: A tuple where the
                first element is a list of required dependencies and the
                second element is a list of optional dependencies
        """
        if "num_strands" not in config.attributes.fields:
            raise Exception(
                "A num_strands attribute is required for multi led component. Must be an integer. This is the number of led strips"
            )

        if "strand_length" not in config.attributes.fields:
            raise Exception(
                "A strand_length attribute is required for multi led component. Must be an integer. This is the number of pixels per strip."
            )

        if "brightness" not in config.attributes.fields:
            raise Exception(
                "A brightness attribute is required for multi led component component. Must be a float like 0.2 for 20% brightness"
            )

        if "address" not in config.attributes.fields:
            raise Exception(
                "A address attribute is required for multi led component. It should be of format 0xADDRESS"
            )

        return [], []

    async def do_command(
        self,
        command: Mapping[str, ValueTypes],
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, ValueTypes]:
        self.logger.info(f"value passed into do command: {command}")
        return self.send_message(command)
    
    def send_message(self, message):
        byte_string = json.dumps(message).encode("utf-8")
        chunks = divide_chunks(byte_string, MESSAGE_CHUNK_SIZE)
        self.logger.info("sent message over i2c")
        for chunk in chunks:
            self.bus.write_i2c_block_data(self.address, 0x00, chunk)
    
    def convert_int_list_to_string(self, int_list):
        # Convert list of integers to bytes
        byte_data = bytes(int_list)
        
        # Decode bytes to string, stopping at null terminators
        # The 'utf-8' encoding is commonly used, but you might need another one depending on your data
        return byte_data.decode('utf-8').rstrip('\x00')

    async def close(self):
        self.bus.close()


