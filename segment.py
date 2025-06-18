# Importing needed packages (install before use)
import os
import sys
import itk
import logging
import SimpleITK as sitk
import numpy as np

# Set up logging functionality for the script
script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(script_dir, 'project.log')
logger = logging.getLogger()

# Check if the logger already has handlers (to avoid adding multiple handlers)
# Logging handler to write to the user terminal via stderr
if not logger.hasHandlers():
    logger.setLevel(logging.DEBUG)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream handler
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def extract_connected_components(input_file, output_folder,component_size):
    """
    @brief Extracts connected components from an input image
    and saves each as its own file in the specified output folder.

    Reads a (.mha) file, segments out each connected component
    by its label, filters out components smaller than component_size voxels,
    and writes each remaining component back to the specified output folder.

    @param input_file      Path to the source .mha image from which we extract components.
    @param output_folder   Directory where each extracted component
                           file Component<i>.mha will be saved.
    @param component_size  Minimum voxel count threshold; components smaller than this
                           will be discarded.
    @return                Prints a list of full paths (as strings) to the saved component files to stdout for piping.
    @exception RuntimeError  If the input cannot be read or writing any component fails.
    """
    try:
        # Attempt to read the input .mha image
        sitk_image = sitk.ReadImage(input_file)
        sitk_image_cast = sitk.Cast(sitk_image, sitk.sitkUInt16)  # Cast image to 16-bit unsigned integer
        # Log successful image loading
        logging.info(f"Successfully loaded input .mha file: '{input_file}'\n")

    except Exception as e:
        # Log error and exit if the file cannot be loaded
        logging.critical(f"Failed to load .mha file '{input_file}'", exc_info=e)
        sys.exit(1)

    # Convert the SimpleITK image to a NumPy array. We use both SITK and ITK due to incompatabilities
    # regarding some formats/datastructures with ITK
    np_array = sitk.GetArrayFromImage(sitk_image_cast)
    # Convert NumPy array back to an ITK image for further processing
    itk_image = itk.image_view_from_array(np_array)
    input_image = itk_image  # Store input image in an ITK format
    # Determine the number of components
    unique_values = np.unique(np_array)
    number_components = len(unique_values) - 1
    logging.info(" ")
    logging.info("**IMAGE SEGMENTATION**")
    logging.info(" ")
    logging.info(str(number_components) + " unique components in " + os.path.basename(input_file))
    logging.info(" ")

    # Check if the image contains any components
    if number_components == 0:  # No components besides background in the image
        logging.warning("Specified image is empty (i.e., does not contain any components). CTA Model Framework is terminating.")
        sys.exit(1)
    components = [] # all component paths for next stage
    # Save each component as a separate file
    for component_id in range(1, unique_values.size + 1):  # Iterate over all unique component IDs
        try:
            # Apply a binary threshold to extract each component
            component_image = itk.BinaryThresholdImageFilter.New(input_image)
            component_image.SetLowerThreshold(component_id)
            component_image.SetUpperThreshold(component_id)
            component_image.SetInsideValue(1)  # Value for pixels inside component
            component_image.SetOutsideValue(0)  # Value for pixels outside component
            component_image.Update()

            # Count number of voxels in component
            component_voxel_count = np.sum(itk.GetArrayFromImage(component_image))
            if component_voxel_count >= component_size:  # Apply voxel count filter to remove small components
                # Save each relevant component as a separate .mha file
                component_file = os.path.join(output_folder, f"Component{component_id}.mha")
                if os.path.exists(component_file):
                    logger.warning(f"File '{component_file}' already exists. Overwrite? (y/n): ")
                    sys.stderr.flush()  # Ensure prompt is immediately visible to user
                    with open('/dev/tty', 'r') as tty:
                        user_input = tty.readline().strip().lower()
                    if user_input != 'y':
                        # If user does not confirm, we don't further process this component i.e. dont stdout to next stage
                        logger.info("Conversion cancelled by user. File was not overwritten. This component will not be further processed")
                        continue # skip component


                itk.imwrite(component_image.GetOutput(), component_file)  # Write component to file
                components.append(component_file)
                # User feedback: Log information about saved components
                logger.info(f"Component {component_id} saved as {os.path.basename(component_file)}" )

            else:
                # Log warning for components that are too small
                logger.warning(f"Component {component_id} is of insufficient size for image segmentation (voxel count below treshhold) Ignored.")

        except Exception as e:
            # Log error if any issue occurs during component processing
            logger.critical("Failed during processing component: " + f"{component_id}. CTA Model Framework is terminating.", exc_info=e)
            sys.exit(1)

    # We handle the case where user decides not to overwrite any component and no further components to process exist
    if len(components) >= 1:
        for component in components:
            print(component)
    else:
        logger.info("No components to proceed with after segmentation. System will terminate")
        sys.exit(0)

# Read input file path from stdin
input_file = sys.stdin.read().strip()

# Read filtering parameters and desired output folder from the command-line arguments
output_folder = sys.argv[1]
component_size = int(sys.argv[2])

extract_connected_components(input_file, output_folder,component_size)
