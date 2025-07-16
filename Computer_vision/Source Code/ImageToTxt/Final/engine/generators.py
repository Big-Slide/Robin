import cv2
import easyocr
import numpy as np
import os


class TextProcessor:
    def __init__(self):
        # Initialize EasyOCR reader
        self.reader = easyocr.Reader(['fa'])  # Add more languages if needed
        # Define colors for different text types
        self.colors = np.random.randint(0, 255, size=(100, 3), dtype=np.uint8)
        # Define target size for processed images
        self.target_size = 1000

    def resize_maintain_aspect(self, image, target_size):
        """
        Resize image to target size while maintaining aspect ratio
        """
        height, width = image.shape[:2]
        aspect = width / height

        if width > height:
            new_width = target_size
            new_height = int(target_size / aspect)
        else:
            new_height = target_size
            new_width = int(target_size * aspect)

        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

    def draw_ocr_results(self, image, ocr_results):
        """
        Draw bounding boxes and text for OCR results
        Each text box gets a unique color based on its index
        """
        annotated_image = image.copy()
        height, width = annotated_image.shape[:2]

        # Calculate scale factors for text and line thickness
        scale_factor = width / 1000.0
        font_scale = max(0.5, scale_factor)
        line_thickness = max(2, int(scale_factor * 2))

        for idx, (bbox, text, prob) in enumerate(ocr_results):
            # Convert bbox points to integers
            bbox = np.array(bbox).astype(int)

            # Get color for this text box
            color = tuple(map(int, self.colors[idx % len(self.colors)]))

            # Draw polygon around text
            cv2.polylines(annotated_image, [bbox], True, color, line_thickness)

            # Add text and index
            text_position = (bbox[0][0], bbox[0][1] - int(10 * scale_factor))
            cv2.putText(
                annotated_image,
                f"{idx}: {text}",
                text_position,
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                color,
                line_thickness
            )

            # Add confidence score
            conf_position = (bbox[0][0], bbox[0][1] + int(25 * scale_factor))
            cv2.putText(
                annotated_image,
                f"Conf: {prob:.2f}",
                conf_position,
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale * 0.8,
                color,
                max(1, line_thickness - 1)
            )

        return annotated_image

    def perform_skew_correction(self, image):
        """
        Perform skew correction on the image
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

        skew_corrected = False
        corrected_image = image.copy()

        if lines is not None:
            angles = []
            for line in lines:
                x1_line, y1_line, x2_line, y2_line = line[0]
                if x2_line - x1_line != 0:  # Avoid division by zero
                    angle = float(np.arctan2(y2_line - y1_line, x2_line - x1_line) * 180.0 / np.pi)
                    if abs(angle) < 45:  # Consider only roughly horizontal lines
                        angles.append(angle)

            if angles:
                # Calculate median angle to reduce impact of outliers
                median_angle = float(np.median(angles))
                skew_corrected = True

                # Rotate image to correct skew
                center = tuple(np.array(image.shape[1::-1]) / 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                corrected_image = cv2.warpAffine(
                    image,
                    rotation_matrix,
                    image.shape[1::-1],
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )

        return corrected_image, skew_corrected

    def process_image(self, image_input):
        """
        Process an image (file path or numpy array), perform skew correction and OCR,
        and return annotated image with text boxes.
        """
        # Load image
        if isinstance(image_input, str):
            # If input is a file path
            image = cv2.imread(image_input)
            if image is None:
                raise ValueError(f"Could not load image from {image_input}")
        else:
            # If input is already a numpy array
            image = image_input.copy()

        # Perform skew correction
        corrected_image, skew_corrected = self.perform_skew_correction(image)

        # Resize corrected image to target size
        resized_image = self.resize_maintain_aspect(corrected_image, self.target_size)

        # Perform OCR on the resized image
        ocr_results = self.reader.readtext(resized_image)

        # Draw OCR results on the resized image
        annotated_image = self.draw_ocr_results(resized_image, ocr_results)

        # Store results with only index and text (simplified format)
        text_entries = []
        for idx, (bbox, text, prob) in enumerate(ocr_results):
            # Simplified structure with only index and text
            text_entries.append({
                'index': idx,
                'text': text
            })

        text_data = {
            'texts': text_entries,
            'skew_corrected': skew_corrected
        }

        return image, annotated_image, text_data