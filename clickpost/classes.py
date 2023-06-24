import base64
from dataclasses import dataclass
from __future__ import print_function

from typing import Optional

import clicksend_client
from clicksend_client import PostRecipient
from clicksend_client.rest import ApiException, RESTResponse
from clicksend_client.models import Address, PostLetter, UploadFile, Url
from clicksend_client.api import AccountApi, PostLetterApi, PostReturnAddressApi, UploadApi
from clicksend_client.configuration import Configuration
import json
import functools




class ClickSend:
    configuration = Configuration()
    client = None
    default_return = None
    def __init__(self):
        self.configuration.username = 'lewis@quickstripe.co.uk'
        self.configuration.password = '5584F742-DC9C-F051-894D-59F052C31F95'
        self.client = clicksend_client.ApiClient(self.configuration)
        self.default_return = self.get_return_address_list(default=True)
    def convert_json_out(*keys):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                result = func(self, *args, **kwargs)
                if isinstance(result, str):
                    try:
                        result = json.loads(
                            result.replace("'", '"').replace("True", 'true').replace("False", 'false').replace("None",
                                                                                                               'null'))
                    except:
                        return result

                        # Access nested data based on the provided keys
                nested_data = result
                for key in keys:
                    if isinstance(nested_data, dict):
                        nested_data = nested_data.get(key)
                    elif isinstance(nested_data, list):
                        if isinstance(key, int) and key < len(nested_data):
                            nested_data = nested_data[key]
                        else:
                            nested_data = None
                    else:
                        nested_data = None

                return nested_data

            return wrapper

        return decorator

    @convert_json_out()
    def create_return_addresses(self, address: [Address]):

        api_instance = PostReturnAddressApi(self.client)
        return_address = Address(**address)  # Address | Address model
        try:
            # Create post return address
            api_response = api_instance.post_return_addresses_post(return_address)
            return api_response
        except ApiException as e:
            return e.json()

    @convert_json_out()
    def get_return_address_list(self, page=1, limit=10, default=False):
        """
        Gets a list of all return addresses
        """

        # create an instance of the API class
        api_instance = PostReturnAddressApi(self.client)

        try:
            # Get list of post return addresses
            api_response = api_instance.post_return_addresses_get(page=page, limit=limit)
            return api_response if not default else api_response["data"]["data"][0]
        except ApiException as e:
            return e

    @convert_json_out()
    def _upload_document(self, file_location: str):

        def convert_pdf_to_base64():
            """Converts the file to base64 if it exists"""
            try:
                with open(file_location, 'rb') as file:
                    pdf_bytes = file.read()
                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    return base64_pdf
            except FileNotFoundError:
                raise FileNotFoundError(f"The file '{file_location}' does not exist.")
            except Exception as e:
                raise RuntimeError(f"Failed to convert PDF to Base64: {e}")
        # sets the upload api
        api_instance: UploadApi = UploadApi(self.client)
        # gets the instance of the file and converts to base_64 as required
        upload_file: UploadFile = UploadFile(content=convert_pdf_to_base64())
        # converts to a postage type
        convert = "post"
        try:
            # Upload File
            api_response = api_instance.uploads_post(upload_file, convert)
            return api_response
        except ApiException as e:
            return e

    @convert_json_out()
    def send_letter(self, address: [Address], file_location=None, price_only=False, **kwargs):

        # do checks
        assert file_location is not None, "You must supply either a url or a file location"
        assert isinstance(address, Address), "You must supply an address object"

        if "return_id" not in kwargs:
            return_id = self.get_return_address_list()["data"][0]
        else:
            return_id = kwargs["return_id"]

        # upload or get the location of the file
        if "http" in file_location:
            upload_url = file_location
        else:
            upload_data = self._upload_document(file_location)
            upload_url = ""


        # create an instance of the API class and post recipient to send
        api_instance = PostLetterApi(self.client)
        post_recipient = PostRecipient(**address, return_address_id=return_id, schedule=0)

        # Actually confirm the postage
        post_letter = PostLetter(
            file_url=upload_url,
            template_used=1,
            colour=kwargs["colour"] if "colour" in kwargs else 0,
            duplex=kwargs["duplex"] if "duplex" in kwargs else 1,
            recipients=[post_recipient])


        # if its price only it will return the price
        if price_only:
            return self._check_price(address, post_letter, **kwargs)

        try:
            # Send post letter
            api_response = api_instance.post_letters_send_post(post_letter)
            return api_response
        except ApiException as e:
            return e

    def _check_price(self, post_letter: PostLetter):
        """

        :param post_letter [PostLetter]: a PostLetter object
        :return: price to send
        """
        api_instance = PostLetterApi(self.client)

        try:
            # Calculate post letter price
            api_response = api_instance.post_letters_price_post(post_letter)
            return api_response
        except ApiException as e:
            return e
