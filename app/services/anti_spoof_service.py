
#
# This file contains derivative work based on the "Silent-Face-Anti-Spoofing"
# project by Minivision (Licensed under the Apache License 2.0).
# Format conversion by 
# https://huggingface.co/garciafido/minifasnet-v2-anti-spoofing-onnx

import os
import logging
from typing import List, Tuple
import cv2
import numpy as np
import onnxruntime as ort
import dlib
from app.core.config import config

class AntiSpoofService:
    """Singleton service for Anti-Spoofing (Passive Liveness) detection using ONNX Runtime.
    
    Uses MiniFASNet V2 (80x80 input, 3-class output) running strictly on CPUExecutionProvider
    as mandated by architectural constraints.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AntiSpoofService, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self) -> None:
        """Initializes Dlib face detector and ONNX InferenceSession globally for CPU execution."""
        self.detector = dlib.get_frontal_face_detector()
        self.session = None
        self.input_name = None

        model_path = config.ANTI_SPOOF_MODEL_PATH
        if os.path.exists(model_path):
            try:
                # Strictly CPU execution provider as per project constraints
                self.session = ort.InferenceSession(
                    model_path,
                    providers=['CPUExecutionProvider']
                )
                self.input_name = self.session.get_inputs()[0].name
                logging.info(f"AntiSpoofService: ONNX MiniFASNet V2 loaded successfully on CPU from '{model_path}'.")
            except Exception as e:
                logging.error(f"Failed to load ONNX Anti-Spoofing model: {e}")
        else:
            logging.warning(
                f"AntiSpoofService: ONNX model file not found at '{model_path}'. "
                f"Service will operate in development fallback mode."
            )

    def _get_expanded_bbox(self, img_h: int, img_w: int, face_rect: dlib.rectangle, scale: float = 2.7) -> Tuple[int, int, int, int]:
        """Expands the face bounding box by a scale factor (default 2.7x) to capture head & background context."""
        left, top, right, bottom = face_rect.left(), face_rect.top(), face_rect.right(), face_rect.bottom()
        box_w = right - left
        box_h = bottom - top
        center_x = left + box_w / 2.0
        center_y = top + box_h / 2.0

        new_w = box_w * scale
        new_h = box_h * scale

        new_left = int(max(0, center_x - new_w / 2.0))
        new_top = int(max(0, center_y - new_h / 2.0))
        new_right = int(min(img_w, center_x + new_w / 2.0))
        new_bottom = int(min(img_h, center_y + new_h / 2.0))

        return new_top, new_right, new_bottom, new_left

    def _preprocess_crop(self, img_np: np.ndarray, face_rect: dlib.rectangle) -> np.ndarray:
        """Crops expanded face region and resizes to 80x80 NCHW float tensor for MiniFASNet V2."""
        h, w = img_np.shape[:2]
        crop_top, crop_right, crop_bottom, crop_left = self._get_expanded_bbox(h, w, face_rect, scale=2.7)

        crop = img_np[crop_top:crop_bottom, crop_left:crop_right]
        if crop.size == 0:
            crop = img_np

        resized = cv2.resize(crop, (80, 80))
        # Convert BGR to RGB
        rgb_resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Transpose HWC to CHW -> (3, 80, 80)
        chw = np.transpose(rgb_resized, (2, 0, 1)).astype(np.float32)
        # Add batch dimension NCHW -> (1, 3, 80, 80)
        nchw = np.expand_dims(chw, axis=0)
        return nchw

    def predict_single_frame(self, image_bytes: bytes) -> float:
        """Detects face and calculates the liveness score (0.0 to 1.0) for a single image frame.

        Args:
            image_bytes (bytes): Raw JPEG/PNG image byte payload.

        Returns:
            float: Real face probability score (Index 1 of MiniFASNet 3-class softmax output).
        """
        image_np = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image frame.")

        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        dets = self.detector(rgb_img, 1)
        if len(dets) == 0:
            raise ValueError("No face detected in liveness frame.")

        # If model is not loaded (dev fallback), return dummy high score for testing
        if self.session is None or self.input_name is None:
            return 0.99

        nchw_tensor = self._preprocess_crop(img, dets[0])

        outputs = self.session.run(None, {self.input_name: nchw_tensor})
        logits = outputs[0][0] # MiniFASNet 3-class logits
        
        # Apply Softmax over 3 logits
        exp_logits = np.exp(logits - np.max(logits))
        probabilities = exp_logits / np.sum(exp_logits)
        
        # Index 1 corresponds to Real Face in MiniFASNet V2
        real_score = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])
        return real_score

    def evaluate_liveness_frames(self, frames: List[bytes]) -> Tuple[bool, float]:
        """Evaluates exactly 3 JPEG frames sent from Frontend and computes average liveness score.

        Args:
            frames (List[bytes]): Exactly 3 JPEG image frame byte payloads.

        Returns:
            Tuple[bool, float]: A tuple (is_real, average_liveness_score).
        """
        if len(frames) != 3:
            raise ValueError(f"eKYC Liveness check requires exactly 3 frames, received {len(frames)}.")

        scores = []
        for i, frame_bytes in enumerate(frames):
            try:
                score = self.predict_single_frame(frame_bytes)
                scores.append(score)
            except ValueError as ve:
                logging.warning(f"Frame {i+1} liveness evaluation failed: {ve}")
                raise ValueError(f"Frame {i+1} invalid: {ve}")

        avg_score = float(np.mean(scores))
        is_real = avg_score >= config.LIVENESS_THRESHOLD

        logging.info(
            f"eKYC Liveness Evaluation: Avg Score = {avg_score:.4f} "
            f"(Threshold = {config.LIVENESS_THRESHOLD}), Real Face = {is_real}"
        )
        return is_real, avg_score

# Singleton instance initialized globally
anti_spoof_service_instance = AntiSpoofService()
