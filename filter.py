# Importing needed packages (install before use)
import os
import logging
import sys
import itk

# This section sets up logging, logs all levels to a file, and formats log messages
script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(script_dir, 'project.log')
logger = logging.getLogger()

# check if the logger already has handlers (to avoid adding multiple handlers)
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

def anisotropic_diffusion_filtering(component_files, output_folder, time_step=0.0025, conductance=2.5, iterations=32):
    """
    @brief Applies ITK-based anisotropic diffusion filtering to a list of components and saves the results.

    This function reads each input .mha component file, applies a CurvatureAnisotropicDiffusion filter
    with the specified time step, conductance and iteration count, then writes a smoothed .mha file
    to the output folder. If any step fails (reading, filtering, or writing), the process is terminated
    with an error message.

    @param component_files   List of file paths to the .mha component images to be filtered.
    @param output_folder     Directory where each smoothed image (ComponentName_smoothed.mha) will be saved.
    @param time_step         Stability parameter for diffusion filter Default: 0.0025.
    @param conductance       Conductance parameter controlling edge preservation. Higher values allow
                             more smoothing across gradients. Default: 2.5.
    @param iterations        Number of diffusion iterations to perform. More iterations produce stronger smoothing.
                             Default: 32.

    @return                  Prints the full path of each successfully smoothed component to stdout,
                             for downstream pipeline stages.

    @exception RuntimeError  If no components are provided, if a component cannot be read, filtered,
                             or written, a RuntimeError is raised and the program exits.
    """
    logger.info(" ")
    logger.info("**ANISOTROPIC FILTERING**")
    logger.info(" ")

    # Check if there are components to filter
    if len(component_files) == 0:  # No components left after segmentation
        logger.warning(f"No components found for filtering. CTA Model Framework is terminating.")
        sys.exit(1)

    # Apply filter to each component file
    for component_file in component_files:
        # Set absolute path for output smoothed file
        try:
            output_file = os.path.join(output_folder, f"{os.path.basename(component_file).replace('.mha', '_smoothed.mha')}")

            # Set pixel type and image dimension for ITK
            PixelType = itk.F  # Pixel type: float
            Dimension = 3  # Image dimension: 3D
            ImageType = itk.Image[PixelType, Dimension]  # Define the image type

            # Read component image
            reader = itk.ImageFileReader[ImageType].New()
            reader.SetFileName(component_file)

            # Apply anisotropic diffusion filter
            diffusion_filter = itk.CurvatureAnisotropicDiffusionImageFilter[ImageType, ImageType].New()
            diffusion_filter.SetInput(reader.GetOutput())
            diffusion_filter.SetTimeStep(time_step)  # Set time step (stability)
            diffusion_filter.SetConductanceParameter(conductance)  # Set conductance (edge preservation)
            diffusion_filter.SetNumberOfIterations(iterations)  # Set number of iterations for filtering

            # Write smoothed image to output file
            writer = itk.ImageFileWriter[ImageType].New()
            writer.SetFileName(output_file)
            writer.SetInput(diffusion_filter.GetOutput())
            writer.Update()

        except Exception as e:
            # Log error and terminate if image could not be smoothed
            logger.critical(os.path.basename(component_file) + " could not be smoothed. CTA Model Framework is terminating.", exc_info=e)
            sys.exit(1)

        # Log successful filtering and print the output file path
        try:
            logger.info(os.path.basename(component_file) + " successfully smoothed")
            print(component_file)  # Pass the absolute path of the smoothed component to the next pipeline stage via stdout
        except Exception as e:
            # Log error if the file could not be saved after smoothing
            logger.critical(os.path.basename(component_file) + " could not be saved. CTA Model Framework is terminating.", exc_info=e)
            sys.exit(1)


# Read input from the previous pipeline stage. This yields an array of strings, each representing absolute path of a component file
components_dir = [line.strip() for line in sys.stdin]

# Read filtering parameters and desired output folder from the command-line arguments
output_folder = sys.argv[1]
time_step = float(sys.argv[2])
conductance = float(sys.argv[3])
iterations = int(sys.argv[4])

anisotropic_diffusion_filtering(components_dir, output_folder, time_step, conductance, iterations)
