"""
Model Analyzer - Extracts real properties from a Fusion 360 design
"""

import adsk.core
import adsk.fusion


class ModelAnalyzer:

    def __init__(self, design):
        self.design = design
        self.root = design.rootComponent

    def analyze(self):
        return {
            "current_mass":     self._mass(),
            "volume":           self._volume(),
            "bounding_box":     self._bbox(),
            "bodies_count":     self.root.bRepBodies.count,
            "components_count": self.root.occurrences.count,
            "can_shell":        self._can_shell(),
            "features":         self._features(),
            "material":         self._material(),
            "surface_area":     self._surface_area(),
            "wall_thickness_estimate": self._wall_thickness_estimate(),
        }

    def _mass(self):
        try:
            total = 0
            for body in self.root.bRepBodies:
                total += body.physicalProperties.mass * 1000  # kg → g
            return round(total, 2)
        except:
            return 0.0

    def _volume(self):
        try:
            total = 0
            for body in self.root.bRepBodies:
                total += body.physicalProperties.volume * 1e6  # m³ → cm³
            return round(total, 2)
        except:
            return 0.0

    def _bbox(self):
        try:
            b = self.root.boundingBox
            return {
                "x": round((b.maxPoint.x - b.minPoint.x) * 10, 2),  # cm → mm
                "y": round((b.maxPoint.y - b.minPoint.y) * 10, 2),
                "z": round((b.maxPoint.z - b.minPoint.z) * 10, 2),
            }
        except:
            return {"x": 0, "y": 0, "z": 0}

    def _can_shell(self):
        try:
            return any(b.isSolid for b in self.root.bRepBodies)
        except:
            return False

    def _features(self):
        try:
            f = self.root.features
            return {
                "extrudes":  f.extrudeFeatures.count,
                "revolves":  f.revolveFeatures.count,
                "holes":     f.holeFeatures.count,
                "fillets":   f.filletFeatures.count,
                "chamfers":  f.chamferFeatures.count,
                "shells":    f.shellFeatures.count,
                "patterns":  (f.rectangularPatternFeatures.count +
                              f.circularPatternFeatures.count),
            }
        except:
            return {}

    def _material(self):
        try:
            for body in self.root.bRepBodies:
                if body.material:
                    return body.material.name
            return "No material assigned"
        except:
            return "Unknown"

    def _surface_area(self):
        try:
            total = 0
            for body in self.root.bRepBodies:
                total += body.physicalProperties.area * 1e4  # m² → cm²
            return round(total, 2)
        except:
            return 0.0

    def _wall_thickness_estimate(self):
        """
        Rough wall thickness estimate based on volume vs surface area.
        Real FEA would give better results.
        """
        try:
            vol = self._volume()   # cm³
            area = self._surface_area()  # cm²
            if area > 0:
                return round((vol / area) * 10, 2)  # mm
            return None
        except:
            return None
