# Importing needed packages (install before use)
import os
import logging
import sys
import itk
import vtk

# This section sets up logging, logs all levels to a file, and formats log messages
script_dir = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(script_dir, 'project.log')
logger = logging.getLogger()

# Check if the logger already has handlers (to avoid adding multiple handlers)
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

def generate_mesh(components, contour_value=0.5):
    """
    @brief Generate a VTK surface mesh from each smoothed component image.

    For every entry in the components list (each a smoothed .mha file), this function:
    1. Converts the ITK image to VTK image data.
    2. Uses vtkContourFilter with the specified contour_value to extract an isosurface.
    3. Writes the resulting mesh to a .vtk file in the same directory.

    @param components
        A list of file paths to smoothed component images (each ending in “_smoothed.mha”).
    @param contour_value
        The scalar threshold passed to vtkContourFilter when extracting the surface
        (default is 0.5).

    @return
        Prints the full path of each generated .vtk mesh file to stdout so that
        downstream pipeline stages can read the filenames.

    @exception RuntimeError
        If any step of mesh generation fails (reading, contour extraction, or writing),
        an error message is sent to stderr and the program exits.
    """
    logger.info(" ")
    logger.info("**MESH GENERATION**")
    logger.info(" ")

    # Generate mesh for each smoothed component
    for component_file in components:
        try:
            # Derive the smoothed file and output mesh file paths
            smoothed_file = f"{os.path.splitext(component_file)[0]}_smoothed.mha"
            output_file = os.path.join(os.path.dirname(component_file), f"{os.path.basename(smoothed_file).replace('_smoothed.mha', '.vtk')}")

            # Convert ITK image to VTK image data
            inputImage = itk.imread(smoothed_file)  # Read smoothed component file using ITK
            vtkImage = itk.vtk_image_from_image(inputImage)  # Convert ITK image to VTK image

            # Set up VTK contour filter to extract mesh
            contourFilter = vtk.vtkContourFilter()
            contourFilter.SetInputData(vtkImage)  # Set input VTK image data
            contourFilter.SetValue(0, contour_value)  # Set contour value for mesh extraction

            # Perform contour extraction
            contourFilter.Update()  # Run filter to extract the mesh
            mesh = contourFilter.GetOutput()  # Get resulting mesh

        except Exception as e:
            # If an error occurs during mesh generation, log it and terminate
            logger.critical("TIN mesh could not be generated for: " + os.path.basename(component_file) + ". CTA Model Framework is terminating", exc_info=e)
            sys.exit(1)

        # Save the generated mesh to a .vtk file
        try:
            writer = vtk.vtkPolyDataWriter()
            writer.SetFileName(output_file)
            writer.SetInputData(mesh)
            writer.Write()  # Write the mesh to the file

            # User feedback: log and print mesh file path to stdout for the pipe
            logger.info("TIN net saved for " + os.path.basename(smoothed_file))
            print(output_file)  # Print the path of the generated mesh file to stdout for the next pipeline stage

        except Exception as e:
            # If an error occurs during saving, log it and terminate
            logger.critical("TIN mesh could not be saved for: " + os.path.basename(component_file) + ". CTA Model Framework is terminating",exc_info=e)
            sys.exit(1)

# Read input components from stdin (absolute paths of smoothed component files)
components = [line.strip() for line in sys.stdin]

# Read contour value from the command-line arguments
contour_value = float(sys.argv[1])  # The contour value to be used for mesh extraction

generate_mesh(components, contour_value)
