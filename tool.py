
import matplotlib
import matplotlib.pyplot as plt
import logging
import numpy as np
import os

from subprocess import call

from qmenta.imaging.processing.report_utils.report_tools import (
    generate_pdf_report, generate_online_report
)
from qmenta.report.html_snippets.build_html_tables import (
    table_double_header_and_images
)
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


class MockTool(Tool):
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
        self.prepare_inputs(context, logger)
        analysis_data = context.fetch_analysis_data()
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
        t1_path = os.path.join(out_folder, "T1_final.nii.gz")
        histogram_data_path = '/root/hist.txt'
        call([
            "/usr/lib/mrtrix/bin/mrstats",
            "-histogram", histogram_data_path,
            "-bins", "50",
            t1_path
        ])
        # Plot the histogram for the selected range of intensities
        [bins_centers, values] = np.loadtxt(histogram_data_path)

        _, ax = plt.subplots()
        ax.set_title("T1 Histogram (for intensities between 50 and 400)")
        ax.set_ylabel("Number of voxels")
        ax.grid(color="#CCCCCC", linestyle="--", linewidth=1)

        left_i = next(i for i,v in enumerate(bins_centers) if v > hist_start)
        right_i = max((i for i,v in enumerate(bins_centers) if v < hist_end))

        plt.plot(bins_centers[left_i:right_i], values[left_i:right_i])

        hist_path = os.path.join(working_dir, "hist.png")
        plt.savefig(hist_path)
        self.upload_output_file(
            context=context,
            source_file_path=hist_path,  # path to the output file in Docker container
            destination_path="hist.png",  # path of the file saved in the output container in the platform
        )
        # Generate an example report
        # Since it is a head-less machine, it requires Xvfb to generate the pdf
        context.set_progress(message="Creating report...")
        html_content = table_double_header_and_images(
            [hist_path],
            ["axial", "coronal", "sagittal"],
            subtitle_alignment="center",
            title="histogram",
            type_colors="primary",
            caption="Fifth table comparison with primary colors and images",
        )
        report_path = os.path.join(working_dir, "online_report.html")
        # Here all the images have the full path, is important that before
        # upload you rename them to the relative path
        # inside the output container
        html_content_online = html_content.replace(os.path.dirname(hist_path) + "/", "")
        generate_online_report(report_online_contents=html_content_online,
                               report_path=report_path)
        generate_online_report()
        self.upload_output_file(
            context=context,
            source_file_path=report_path,  # path to the output file in Docker container
            destination_path=os.path.basename(report_path),  # path of the file saved in the output container in the platform
            tags={"report"}
        )
        report_path = os.path.join(working_dir, "report.pdf")
        html_content_pdf = generate_pdf_report(
            report_contents=html_content,
            analysis_data=analysis_data,
            analysis_title="Histogram report v1.0",  # limit 32 characters
            report_path=report_path,
        )
        self.upload_output_file(
            context=context,
            source_file_path=report_path,  # path to the output file in Docker container
            destination_path=os.path.basename(report_path),  # path of the file saved in the output container in the platform
        )
        # DEBUG
        with open(os.path.join(out_folder, "report_pdf.html"), "w") as f1:
            f1.write(html_content_pdf)
        # ================##

        # PREPARE AND UPLOAD YOUR RESULTS Example:
        context.set_progress(message="Uploading result")
        self.upload_output_file(
            context=context,
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

        # To create a split, specify which ones are the objects to be shown in the split
        split_1 = Split(
            orientation=OrientationLayout.vertical, children=[papaya_1],
            button_label="Images"
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
    MockTool().tool_outputs()  # this can be removed if no results configuration file needs to be generated.
    MockTool().run(context)