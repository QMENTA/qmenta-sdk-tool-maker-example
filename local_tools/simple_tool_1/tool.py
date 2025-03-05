
import logging
import os

from qmenta.sdk.tool_maker.outputs import (
    Coloring,
    HtmlInject,
    OrientationLayout,
    PapayaViewer,
    Region,
    ResultsConfiguration,
    Split,
    Tab,
)
from qmenta.sdk.tool_maker.modalities import Modality, Tag
from qmenta.sdk.tool_maker.tool_maker import InputFile, Tool, FilterFile


class SimpleTool1(Tool):
    def tool_inputs(self):
        """
        Define the inputs for the tool. This is used to create the settings.json file.
        More information on the inputs can be found here:
        https://docs.qmenta.com/sdk/guides_docs/settings.html
        """
        # Add the file selection method:
        self.add_input_container(
            title="Input T1 data",
            info="Requires a T1 image.",
            anchor=1,
            batch=1,
            container_id="input_t1",
            mandatory=1,
            file_list=[
                InputFile(
                    file_filter_condition_name="c_t1",
                    filter_file=FilterFile(
                        modality=Modality.T1
                    ),
                    mandatory=1,
                    min_files=1,
                    max_files=1,
                ),
            ],
        )

        # Displays a horizontal line
        self.add_line()

        # Display a text in the settings explaining the below parameters:
        self.add_info("Parameters of the tool")

        # Display a checkbox parameter
        self.add_input_checkbox(id_="perform_operation_1", default=1, title="Perform operation?")

        # Displays a header text
        self.add_indent("Choice parameters:")

        self.add_input_integer(id_="int_1", default=32, title="First", minimum=0, maximum=100)
        self.add_input_integer(id_="int_2", default=10, title="Second", minimum=0, maximum=100)

        self.add_indent("Select operation.")

        # Adds a dropdown menu for the user to select a single option
        self.add_input_single_choice(
            id_="operation", options=[("add", "Add"), ("mult", "Multiplication")], default="mult",
            title="Single choice type description (add or multiply)"
        )

    def run(self, context):
        """
        This is the main function that is called when the tool is run.
        """
        # ================ #
        # GETTING THINGS READY
        logger = logging.getLogger("main")
        logger.info("Tool starting")

        # Downloads all the files and populate the variable self.inputs with the handlers and parameters
        context.set_progress(message="Downloading input data (Hello)")
        self.prepare_inputs(context, logger)

        t1_handlers = self.inputs.input_t1.c_t1

        t1_path = t1_handlers[0].file_path  # getting the first element of the file handler list

        t1_modality = t1_handlers[0].get_file_modality()

        logger.info(
            f"Input file data."
            f"Path : {t1_path}"
            f"Modality: {t1_modality}"
        )

        # Parameters are also accessible through the self.inputs object
        perform_operation = bool(self.inputs.perform_operation_1)
        first_n = self.inputs.int_1
        second_n = self.inputs.int_2
        logger.info(f"Parameter checkbox : {perform_operation}")
        logger.info(f"Parameter integers : {first_n} {second_n}")

        # Working directory
        working_dir = os.environ.get("WORKDIR")  # from Dockerfile, feel free to modify
        out_folder = os.path.join(working_dir, "OUTPUT")
        os.makedirs(out_folder, exist_ok=True)

        # ================##
        # YOUR CODE HERE
        result_file = os.path.join(out_folder, "T1_final.nii.gz")
        logger.info(f"Something happens to {t1_path} and it becomes {result_file}")
        with open(result_file, "w") as f1:
            f1.write("I have been processed.")

        reporting = "Operation was not performed"
        operation_result = None
        if perform_operation:
            context.set_progress(message=f"Operation performed: {self.inputs.operation}")
            logger.info(f"Operation performed: {self.inputs.operation}")
            if self.inputs.operation == "add":  # add
                operation_result = first_n + second_n
            elif self.inputs.operation == "mult":  # multiply
                operation_result = first_n * second_n
            context.set_progress(message="Finished operation")
            reporting = f"Result: {operation_result}"
            logger.info(f"Result: {operation_result}")
        online_report = os.path.join(out_folder, "online_report.html")
        with open(online_report, "w") as f1:
            f1.write(reporting)
        # ================#

        # PREPARE AND UPLOAD YOUR RESULTS Example:

        # Upload input file in the output container
        context.upload_file(
            source_file_path=t1_path,  # path to the output file in Docker container
            destination_path=os.path.basename(t1_path),  # path of the file saved in the output container in the platform
            modality=str(Modality.DTI),  # modality that will be set for that file
            tags={"input"}  # tags that will be set for that file
        )
        context.set_progress(message="Uploading result")
        context.upload_file(
            source_file_path=result_file,  # path to the output file in Docker container
            destination_path=os.path.basename(result_file),  # path of the file saved in the output container in the platform
            modality=str(Modality.T1),  # modality that will be set for that file
            tags={"output"}  # tags that will be set for that file
        )
        context.upload_file(
            source_file_path=online_report,  # path to the output file in Docker container
            destination_path=os.path.basename(online_report),  # path of the file saved in the output container in the platform
            tags={"report"}  # tags that will be set for that file
        )
        context.set_metadata_value(key="metadata_key", value=100)  # metadata value added to the session metadata
        # ================#

    def tool_outputs(self):
        # Main object to create the results configuration object.
        result_conf = ResultsConfiguration()

        # Add the tools to visualize files using the function add_visualization

        # Online 3D volume viewer: visualize DICOM or NIfTI files.
        papaya_1 = PapayaViewer(title="Tissue segmentation over T1", width="50%", region=Region.center, button_label="Viewer")
        # the first viewer's region is defined as center

        # Add as many layers as you want, they are going to be loaded in the order that you add them.
        papaya_1.add_file(file="t'input'", coloring=Coloring.grayscale)  # using the file name
        papaya_1.add_file(file="t'output'", coloring=Coloring.custom)
        # Add the papaya element as a visualization in the results configuration object.
        result_conf.add_visualization(new_element=papaya_1)

        html_online = HtmlInject(width="100%", region=Region.center, button_label="Report")
        html_online.add_html(file="t'report'")
        result_conf.add_visualization(new_element=html_online)

        # Remember to add the button_label in the child objects of the tab.
        tab_1 = Tab(children=[papaya_1, html_online])
        # Call the function generate_results_configuration_file to create the final object that will be saved in the
        # tool path
        result_conf.generate_results_configuration_file(
            build_screen=tab_1, tool_path=self.tool_path, testing_configuration=False
        )

def run(context):
    SimpleTool1().tool_outputs()  # this can be removed if no results configuration file needs to be generated.
    SimpleTool1().run(context)