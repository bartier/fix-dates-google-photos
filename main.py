import os
import json
import datetime
import PIL
from PIL import Image
from PIL.TiffTags import TAGS as TIFFTags
from pillow_heif import register_heif_opener
import piexif
import datetime
import subprocess

register_heif_opener()


# Supported file types
SUPPORTED_IMAGE_TYPES = ['jpg', 'jpeg', 'heic', 'png']
SUPPORTED_VIDEO_TYPES = ['mov', 'mp4']

def timestamp_to_datetime(timestamp):
    """Converts a timestamp string to a datetime object."""
    return datetime.datetime.fromtimestamp(int(timestamp))

def update_video_metadata(video_path, timestamp):
    """Updates the metadata of a video file and changes the file's modified time."""
    try:
        # Convert the timestamp to the appropriate format for FFmpeg (ISO 8601)
        formatted_date = timestamp_to_datetime(timestamp).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Create a temporary file path
        temp_file = video_path + "_temp" + os.path.splitext(video_path)[1]

        # Build the FFmpeg command to update the creation_time metadata
        command = [
            "ffmpeg",
            "-i", video_path,
            "-metadata", f"creation_time={formatted_date}",
            "-codec", "copy",
            temp_file,
            "-y"  # Overwrite output files without asking
        ]

        # Execute the command
        subprocess.run(command, check=True)

        # Replace the original file with the updated file
        os.replace(temp_file, video_path)

        # Update the file's modified time
        change_file_modified_time(video_path, timestamp)
        print(f"Updated video metadata for: {video_path}")

    except Exception as e:
        print(f"Failed to update video metadata for {video_path}: {e}")


def update_image_metadata(image_path, timestamp):
    """Updates the EXIF, JFIF, TIFF metadata of an image file and changes the file's modified time."""
    try:
        img = Image.open(image_path)
        formatted_date = timestamp_to_datetime(timestamp).strftime("%Y:%m:%d %H:%M:%S")

        # Update EXIF metadata
        exif_data = img.info.get('exif')
        if exif_data:
            exif_dict = piexif.load(exif_data)
        else:
            exif_dict = {"Exif": {}}
        
        # Update DateTimeOriginal in EXIF
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = formatted_date.encode()
        
        # Save EXIF data back to the image
        exif_bytes = piexif.dump(exif_dict)
        img.save(image_path, "jpeg", exif=exif_bytes)

        # Update TIFF metadata (if the image has TIFF tags, e.g., for TIFF images)
        if isinstance(img, PIL.TiffImagePlugin.TiffImageFile):
            tiff_metadata = img.tag_v2
            tiff_metadata[TIFFTags.get("DateTime", 306)] = formatted_date
            img.save(image_path, "tiff")
            print(f"Updated TIFF metadata for image: {image_path}")
        
        # Change the file's modified time
        change_file_modified_time(image_path, timestamp)
        
    except Exception as e:
        print(f"Failed to update image metadata for {image_path}: {e}")

def change_file_modified_time(file_path, timestamp):
    """Updates the file's last modified and access time based on the timestamp."""
    try:
        # Convert the timestamp to a float representing seconds since the epoch
        new_time = int(timestamp)
        os.utime(file_path, (new_time, new_time))  # Sets both access and modified times to new_time
        print(f"Updated file modification time for: {file_path}")
    except Exception as e:
        print(f"Failed to update file modification time for {file_path}: {e}")

def process_directory(root_dir):
    """Recursively processes all directories to find and update files based on JSON."""
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.json'):
                json_file_path = os.path.join(dirpath, filename)

                media_file_path = json_file_path

                if '(' in json_file_path:
                    media_file_path = media_file_path.replace('.PNG(1).json', '(1).PNG')
                    media_file_path = media_file_path.replace('.JPG(1).json', '(1).JPG')
                    media_file_path = media_file_path.replace('.JPEG(1).json', '(1).JPEG')
                    media_file_path = media_file_path.replace('.HEIC(1).json', '(1).HEIC')
                    media_file_path = media_file_path.replace('.MOV(1).json', '(1).MOV')
                    media_file_path = media_file_path.replace('.MP4(1).json', '(1).MP4')
                else:
                    media_file_path = json_file_path.replace('.json', '')

                if media_file_path:
                    # Process the JSON file to get the timestamp
                    with open(json_file_path, 'r') as json_file:
                        data = json.load(json_file)
                        photo_taken_time = data.get("photoTakenTime", {})
                        timestamp = photo_taken_time.get("timestamp")
                        
                        if timestamp:
                            # Update metadata based on file type
                            if media_file_path.lower().endswith(tuple(SUPPORTED_IMAGE_TYPES)):
                                update_image_metadata(media_file_path, timestamp)
                            elif media_file_path.lower().endswith(tuple(SUPPORTED_VIDEO_TYPES)):
                                update_video_metadata(media_file_path, timestamp)
                else:
                    print(f"No matching media file found for JSON: {json_file_path}")

if __name__ == "__main__":
    root_directory = "/Users/vitor/Library/CloudStorage/OneDrive-Personal/Takeout/Google Fotos"
    # root_directory = "/Users/vitor/Development/Personal/fix-dates-google-photos"  # Set this to the top-level directory you want to scan
    process_directory(root_directory)

