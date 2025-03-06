
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


class TemplateToolMaker(Tool):
    def tool_inputs(self):
        """
        Define the inputs for the tool. This is used to create the settings.json file.
        More information on the inputs can be found here:
        https://docs.qmenta.com/sdk/guides_docs/settings.html
        """
        # Add the file selection method:
        self.add_input_container(
            title="Title of the setting",
            info="Describe here what is the expected input, this will appear in the tool UI.",
            anchor=1,
            batch=1,
            container_id="input_data",
            mandatory=1,
            tool_codes_set_as_input=[
                "freesurfer_v5", "freesurfer_v6"
            ],  # Optional - If it takes input from a tool with code freesurfer_v5 or freesurfer_v6.
            file_list=[
                InputFile(
                    file_filter_condition_name="condition_t1_brain",
                    filter_file=FilterFile(
                        modality=Modality.T1,
                        tags=[Tag("brain")],
                        regex=".*",
                    ),
                    mandatory=1,
                    min_files=1,
                    max_files=1,
                ),
            ],
        )

        # The following calls will add different parameters to the settings JSON. Keep, edit or remove them
        # according to your specifications:

        # Display a text in the settings explaining the below parameters:
        self.add_indent("Parameters of the tool are accessed using the variable self.inputs.id_")

        # Display a checkbox parameter
        self.add_input_checkbox(id_="ex_checkbox", default=0, title="Checkbox setting type description")

        # Displays a short free text to input a string parameter
        self.add_input_string(id_="some_string", default="TOOL", title="String type description")

        # Displays a short free text to input a parameter of type integer
        self.add_input_integer(id_="some_integer", default=3, title="Integer type description", minimum=0, maximum=10)

        # Displays an horizontal line
        self.add_line()

        # Displays a short free text to input a parameter of type decimal
        self.add_input_decimal(
            id_="some_decimal", default=3.14, title="Decimal type description", minimum=0.1, maximum=4.3
        )

        # Displays a header text
        self.add_heading("Choice settings:")

        # Displays a text box in blue color with the information specified.
        self.add_info(
            "In the options, the first element in the list of tuples is the value representation that the "
            "tool handles, the second element is the string shown in the platform for humans to select."
        )

        # Adds a dropdown menu for the user to select a single option
        self.add_input_single_choice(
            id_="one_choice", options=[("a", "Option A"), ("b", "Option B"), ("c", "Option C")], default="b",
            title="Single choice type description"
        )

        # Displays a small menu where the user can select multiple options.
        self.add_input_multiple_choice(
            id_="multi_choice",
            options=[("a", "Option A"), ("b", "Option B"), ("c", "Option C")], default=["a", "b"],
            title="Multiple choice type description",
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
        context.set_progress(message="Downloading input data and setting self.inputs object")
        self.prepare_inputs(context, logger)

        # Input handlers are built as simplenamespaces, each attribute is the "id" defined in each InputFile
        # THESE ARE LISTS, each element has the methods to get modality, tags, file_info
        schema_file = self.inputs.input_data.condition_t1_brain

        schema_file_path = schema_file[0].file_path  # getting the first element of the file handler list

        schema_file_modality = schema_file[0].get_file_modality()
        schema_file_tags = schema_file[0].get_file_tags()
        schema_file_file_info = schema_file[0].get_file_info()

        logger.info(
            f"Input file data."
            f"Path : {schema_file_path}"
            f"Modality: {schema_file_modality}"
            f"Tags: {schema_file_tags}"
            f"INFO: {schema_file_file_info}"
        )

        # Parameters are also accessible through the self.inputs object
        checkbox = self.inputs.ex_checkbox
        some_decimal = self.inputs.some_decimal
        logger.info(f"Parameter checkbox : {checkbox}")
        logger.info(f"Parameter decimal : {some_decimal}")

        # Working directory
        working_dir = os.environ.get("WORKDIR")  # from Dockerfile, feel free to modify
        out_folder = os.path.join(working_dir, "OUTPUT")
        os.makedirs(out_folder, exist_ok=True)

        # ================##
        # YOUR CODE HERE
        result_file = os.path.join(out_folder, "T1_final.nii.gz")
        with open(result_file, "w") as f1:
            f1.write("I have been processed.")
        # ================##

        # PREPARE AND UPLOAD YOUR RESULTS Example:
        context.set_progress(message="Uploading result")
        context.upload_file(
            source_file_path=result_file,  # path to the output file in Docker container
            destination_path="T1_final.nii.gz",  # path of the file saved in the output container in the platform
            modality=str(Modality.DTI.value),  # modality that will be set for that file
            tags={"eddy"}  # tags that will be set for that file
        )
        context.set_metadata_value(key="metadata_key", value=100)  # metadata value added to the session metadata
        # ================##

    def tool_outputs(self):
        # Main object to create the results configuration object.
        result_conf = ResultsConfiguration()

        # Add the tools to visualize files using the function add_visualization

        # Online 3D volume viewer: visualize DICOM or NIfTI files.
        papaya_1 = PapayaViewer(title="Tissue segmentation over T1", width="50%", region=Region.center)
        # the first viewer's region is defined as center

        # Add as many layers as you want, they are going to be loaded in the order that you add them.
        papaya_1.add_file(file="T1brain.nii.gz", coloring=Coloring.grayscale)  # using the file name
        papaya_1.add_file(file="tissueSegmentation.nii.gz", coloring=Coloring.custom)
        # Add the papaya element as a visualization in the results configuration object.
        result_conf.add_visualization(new_element=papaya_1)

        papaya_2 = PapayaViewer(title="Labels segmentation over T1", width="50%", region=Region.right)
        # the second viewer's region is defined as right, this depends on the Split(), which has the element
        # orientation set to vertical. If it is set to horizontal, then you can choose between 'top' or 'bottom'.

        # You can use modality or tag of the output file to select the file to be shown in the viewer.
        papaya_2.add_file(file="m'T1'", coloring=Coloring.grayscale)  # using the file modality
        papaya_2.add_file(file="t'seg'", coloring=Coloring.custom_random)  # using file tag
        result_conf.add_visualization(new_element=papaya_2)

        # To create a split, specify which ones are the objects to be shown in the split
        split_1 = Split(
            orientation=OrientationLayout.vertical, children=[papaya_1, papaya_2], button_label="Images"
        )
        # The button label is defined because this element goes into a Tab element. The tab's "button_label" property
        # is a label that will appear to select between different viewer elements in the platform.

        html_online = HtmlInject(width="100%", region=Region.center, button_label="Report")
        html_online.add_html(file="online_report.html")
        result_conf.add_visualization(new_element=html_online)

        # Remember to add the button_label in the child objects of the tab.
        tab_1 = Tab(children=[split_1, html_online])
        # Call the function generate_results_configuration_file to create the final object that will be saved in the
        # tool path
        result_conf.generate_results_configuration_file(
            build_screen=tab_1, tool_path=self.tool_path, testing_configuration=False
        )

def run(context):
    TemplateToolMaker().tool_outputs()  # this can be removed if no results configuration file needs to be generated.
    TemplateToolMaker().run(context)