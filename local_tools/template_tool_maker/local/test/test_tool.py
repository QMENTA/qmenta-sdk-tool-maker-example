import inspect
import unittest
import os

from qmenta.sdk.tool_maker.context import TestFileInput
from qmenta.sdk.tool_maker.modalities import Modality, Tag
import sys
sys.path.append("local_tools")
from template_tool_maker.tool import TemplateToolMaker


class TestTool(unittest.TestCase):
    """Tests for the Tool.
    Execute this test in the same folder where the folder "local_tools" is created
    $ pytest local_tools/template_tool_maker/local/test/test_tool.py::TestTool::test_basic_call
    """

    def test_basic_call(self):
        """A basic test call"""
        os.environ["WORKDIR"] = os.path.join("local_tools/template_tool_maker/local/test/test_basic_call/execution_folder")
        TemplateToolMaker().test_with_args(
            in_args={
                "test_name": inspect.getframeinfo(inspect.currentframe()).function,  # returns function name
                "sample_data_folder": "sample_data",  # Name of the folder where the test data is stored
                "input_data": {
                    "files": [
                        # Relative paths to the input data stored in the sample_data folder
                        TestFileInput(
                            path="T1.nii.gz",
                            file_filter_condition_name="condition_t1_brain",
                            modality=Modality.T1,
                            tags=[Tag("brain")],
                            mandatory=1
                        )
                    ],
                    "mandatory": 1,
                },
                "some_string": "hello",
                "some_integer": 2,
                "one_choice": "a",
                "multi_choice": ["b", "c"],
                "some_decimal": 3.52,
            },
            overwrite_settings=True,  # True if you want to overwrite settings.json
            refresh_test_data=True  # True will remove all data from previous test
        )


class TestToolDocker(unittest.TestCase):
    """
    Once the previous test is executed successfully, this test can be run using a docker container.
    A docker image with the same name as the tool ID is going to be created and the tool will run inside it.
    Once it finishes, you can push the docker image into your registry using docker push.

    The notation for associating a local Docker image with a repository on a registry is:
    username/repository:tag

    However, for clarity reasons, this documentation uses the following syntax to name images:
    username/tool_name:version

    Push the image:
    docker push username/template_tool_maker:1.0
    """

    def test_basic_call(self):
        """A basic test call"""
        TemplateToolMaker().test_docker_with_args(
            in_args={
                "test_name": inspect.getframeinfo(inspect.currentframe()).function,  # returns function name
            },
            version="1.0",
            stop_container=True,
            delete_container=True,
            attach_container=True,
        )