# Importing needed packages (install before use)
import sys
import os
import logging
import SimpleITK as sitk
"""
@brief Implementing and configuring logging functionality for the script.
@brief We generate a log file which is flushed at the beginning of each launch. 
@brief This is also done at the beginning of the other pipeline stages to come.
@brief Regarding the log file, we print to stderr to print both to the command line and log file
"""
script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(script_dir, 'project.log')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Logging handler to write to the user terminal via stderr
if not logger.handlers:
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Stream handler (INFO and above → stderr)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def convert_nii_to_mha(input_nii_path, output_mha_path):
    """
    @brief Convert a NIfTI (.nii) image to MetaImage (.mha) format with overwrite protection.

    Reads the specified .nii file using SimpleITK, constructs an output filename in the given
    directory and writes the image as a .mha file. If the target .mha already exists, the user
    is prompted to confirm before overwriting.

    @param input_nii_path
        Full path to source (.nii) file. If reading this file fails, the function
        terminates with an error.
    @param output_mha_path
        Directory where the converted MetaImage (.mha) file will be written. The output filename
        is derived from the base name of `input_nii_path`. If this directory is not writable
        or the user declines to overwrite, the function exits without writing.

    @return
        Prints the full path of the newly created .mha file to stdout for downstream processing.

    @exception RuntimeError
        Raised if the input file cannot be read, if writing to the output path fails, or if
        the user declines to overwrite an existing file.

    @note
        Converting from NIfTI to MetaImage may drop certain NIfTI-specific metadata.
        A warning is emitted but the image data itself is written correctly. In particular, the use
        case of this script is not affected.
    """
    file_name = os.path.splitext(os.path.basename(input_nii_path))[0]
    try:
        # Read the NIfTI file using SimpleITK
        image = sitk.ReadImage(input_nii_path)
        # Construct final output file path for the MetaImage (.mha) file
        final_path = output_mha_path + "/" + file_name + ".mha"

        # Overwrite protection: Check if the output file already exists
        if os.path.exists(final_path):
            logger.warning(f"File '{final_path}' already exists. Overwrite? (y/n): ")
            sys.stderr.flush()  # Ensure prompt is immediately visible to user
            with open('/dev/tty', 'r') as tty:
                user_input = tty.readline().strip().lower()  # Get user input
            if user_input != 'y':
                # If user does not confirm, cancel conversion and exit
                logger.info("Conversion cancelled by user. File was not overwritten.")
                sys.exit(0)

        # Write the image data to the (.mha) format
        sitk.WriteImage(image, final_path)
        # Log and display success information (warning about metadata loss)
        logger.info("**FILE CONVERSION**")
        logger.info( file_name + " successfully converted to MetaImage" )
        logger.info("Warning about loss of NiFTI metadata can be ignored.")

        # Pass the resulting path to the next pipeline stage via stdout
        print(final_path)

    except Exception as e:
        # Handle errors during the conversion and provide details in the log and error output
        logger.critical(f"ERROR: Failed to convert {file_name} to MetaImage format.", exc_info=e)
        sys.exit(1)

# Reading from the command-line arguments
input_nii = sys.argv[1]
output_path = sys.argv[2]

convert_nii_to_mha(input_nii, output_path)
