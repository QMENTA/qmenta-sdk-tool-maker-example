
import matplotlib
import matplotlib.pyplot as plt
import nibabel as nib
import logging
import numpy as np
import os
import pdfkit
from time import gmtime, strftime
from tornado import template

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
from qmenta.sdk.tool_maker.modalities import Modality
from qmenta.sdk.tool_maker.tool_maker import InputFile, Tool, FilterFile

# This backend config avoids $DISPLAY errors in headless machines
matplotlib.use('Agg')


class QmentaSdkToolMakerExample(Tool):
    def tool_inputs(self):
        """
        Define the inputs for the tool. This is used to create the settings.json file.
        More information on the inputs can be found here:
        https://docs.qmenta.com/sdk/guides_docs/settings.html
        """
        # Add the file selection method:
        self.add_input_container(
            title="T1 weighted image",
            info="Describe here what is the expected input, this will appear in the tool UI.",
            anchor=1,
            batch=1,
            container_id="input",
            mandatory=1,
            tool_codes_set_as_input=[
                "freesurfer_v5", "freesurfer_v6"
            ],  # Optional - If it takes input from a tool with code freesurfer_v5 or freesurfer_v6.
            file_list=[
                InputFile(
                    file_filter_condition_name="c_T1",
                    filter_file=FilterFile(
                        modality=Modality.T1
                    ),
                    mandatory=1,
                    min_files=1,
                    max_files=1,
                ),
            ],
        )

        # The following calls will add different parameters to the settings JSON. Keep, edit or remove them
        # according to your specifications:

        # Displays a short free text to input a parameter of type decimal
        self.add_input_decimal(
            id_="hist_start", default=50, title="From",
            minimum=20, maximum=200
        )

        self.add_input_decimal(
            id_="hist_end", default=400, title="To",
            minimum=250, maximum=500
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
        analysis_data = context.fetch_analysis_data()
        self.prepare_inputs(context, logger)
        # Input handlers are built as simplenamespaces, each attribute is the "id" defined in each InputFile
        # THESE ARE LISTS, each element has the methods to get modality, tags, file_info
        schema_file = self.inputs.input.c_T1

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
        hist_start = self.inputs.hist_start
        hist_end = self.inputs.hist_end
        logger.info(f"histogram start : {hist_start}")
        logger.info(f"Parameter decimal : {hist_end}")

        # Working directory
        working_dir = os.environ.get("WORKDIR")  # from Dockerfile, feel free to modify
        out_folder = os.path.join(working_dir, "OUTPUT")
        os.makedirs(out_folder, exist_ok=True)

        # ================##
        # YOUR CODE HERE
        context.set_progress(message="Processing...")
        t1_path = schema_file_path
        hist_vect = nib.load(t1_path).get_fdata().flatten()
        hist_vect[hist_vect == 0] = np.nan
        # Plot the histogram for the selected range of intensities
        fig, ax = plt.subplots()
        ax.set_title("T1 Histogram (for intensities between 50 and 400)")
        ax.set_ylabel("Number of voxels")
        ax.grid(color="#CCCCCC", linestyle="--", linewidth=1)

        ax.hist(hist_vect, bins=np.arange(hist_start, hist_end, 50))

        hist_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "hist.png")
        fig.savefig(hist_path)
        context.upload_file(
            source_file_path=hist_path,  # path to the output file in Docker container
            destination_path="hist.png",  # path of the file saved in the output container in the platform
        )
        # Generate an example report
        # Since it is a head-less machine, it requires Xvfb to generate the pdf
        context.set_progress(message="Creating report...")
        report_path = os.path.join(working_dir, "report.pdf")
        data_report = {
            "logo_main": "/root/qmenta_logo.png",
            "ss": analysis_data["patient_secret_name"],
            "ssid": analysis_data["ssid"],
            "histogram": hist_path,
            "this_moment": strftime("%Y-%m-%d %H:%M:%S", gmtime()),
            "version": 1.0
        }

        loader = template.Loader(os.path.dirname(os.path.realpath(__file__)))
        report_contents = loader.load("report_template.html").generate(data_report=data_report)

        if isinstance(report_contents, bytes):
            report_contents = report_contents.decode("utf-8")
        pdfkit.from_string(report_contents, report_path, options={"enable-local-file-access": ""})
        context.set_progress(message="Uploading results...")
        context.upload_file(
            source_file_path=report_path,  # path to the output file in Docker container
            destination_path=os.path.basename(report_path),  # path of the file saved in the output container in the platform
            tags={"report"}
        )
        # ================##

        # PREPARE AND UPLOAD YOUR RESULTS Example:
        context.set_progress(message="Uploading result")
        context.upload_file(
            source_file_path=t1_path,  # path to the output file in Docker container
            destination_path="T1_final.nii.gz",  # path of the file saved in the output container in the platform
            modality=str(Modality.DTI),  # modality that will be set for that file
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
        papaya_1.add_file(file="T1_final.nii.gz", coloring=Coloring.grayscale)
        # Add the papaya element as a visualization in the results configuration object.
        result_conf.add_visualization(new_element=papaya_1)
        # Call the function generate_results_configuration_file to create the final object that will be saved in the
        # tool path
        result_conf.generate_results_configuration_file(
            build_screen=papaya_1, tool_path=self.tool_path, testing_configuration=False
        )

def run(context):
    QmentaSdkToolMakerExample().tool_outputs()  # this can be removed if no results configuration file needs to be generated.
    QmentaSdkToolMakerExample().run(context)