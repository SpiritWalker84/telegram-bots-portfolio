"""Utility for loading materials."""
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MaterialLoader:
    """Class for loading course materials."""

    def __init__(self, materials_dir: str = "materials"):
        """
        Initialize material loader.
        
        Args:
            materials_dir: Directory with materials
        """
        self.materials_dir = Path(materials_dir)

    def load_trial_lesson(self) -> str:
        """
        Load trial lesson content.
        
        Returns:
            Trial lesson content as string
            
        Raises:
            FileNotFoundError: If trial lesson file not found
        """
        trial_file = self.materials_dir / "trial_lesson.md"
        
        if not trial_file.exists():
            raise FileNotFoundError(f"Trial lesson file not found: {trial_file}")
        
        try:
            with open(trial_file, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info("Trial lesson loaded successfully")
            return content
        except Exception as e:
            logger.error(f"Error loading trial lesson: {e}")
            raise
