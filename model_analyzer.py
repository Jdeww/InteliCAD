"""
Model Analyzer - Extracts properties and features from Fusion 360 models
"""

import adsk.core
import adsk.fusion


class ModelAnalyzer:
    """
    Analyzes a Fusion 360 design and extracts relevant properties
    """
    
    def __init__(self, design):
        self.design = design
        self.root_comp = design.rootComponent
    
    def analyze(self):
        """
        Perform complete model analysis
        Returns: dict with all analysis data
        """
        return {
            'current_mass': self.get_mass(),
            'volume': self.get_volume(),
            'bounding_box': self.get_bounding_box(),
            'bodies_count': self.get_bodies_count(),
            'components_count': self.get_components_count(),
            'can_shell': self.can_shell(),
            'features': self.get_features(),
            'material': self.get_material(),
            'surface_area': self.get_surface_area()
        }
    
    def get_mass(self):
        """Get total mass in grams"""
        try:
            mass_grams = 0
            
            # Iterate through all bodies
            for body in self.root_comp.bRepBodies:
                # Get physical properties
                props = body.physicalProperties
                mass_grams += props.mass * 1000  # Convert kg to grams
            
            return round(mass_grams, 2)
        except:
            return 0.0
    
    def get_volume(self):
        """Get total volume in cm³"""
        try:
            volume_cm3 = 0
            
            for body in self.root_comp.bRepBodies:
                props = body.physicalProperties
                volume_cm3 += props.volume * 1000000  # Convert m³ to cm³
            
            return round(volume_cm3, 2)
        except:
            return 0.0
    
    def get_bounding_box(self):
        """Get bounding box dimensions in mm"""
        try:
            bbox = self.root_comp.boundingBox
            
            return {
                'x': round((bbox.maxPoint.x - bbox.minPoint.x) * 10, 2),  # cm to mm
                'y': round((bbox.maxPoint.y - bbox.minPoint.y) * 10, 2),
                'z': round((bbox.maxPoint.z - bbox.minPoint.z) * 10, 2)
            }
        except:
            return {'x': 0, 'y': 0, 'z': 0}
    
    def get_bodies_count(self):
        """Get number of solid bodies"""
        return self.root_comp.bRepBodies.count
    
    def get_components_count(self):
        """Get number of components"""
        return self.root_comp.occurrences.count
    
    def can_shell(self):
        """Check if model can be shelled (has solid bodies)"""
        try:
            for body in self.root_comp.bRepBodies:
                if body.isSolid:
                    return True
            return False
        except:
            return False
    
    def get_features(self):
        """Get count of different feature types"""
        try:
            features = {
                'extrudes': self.root_comp.features.extrudeFeatures.count,
                'revolves': self.root_comp.features.revolveFeatures.count,
                'holes': self.root_comp.features.holeFeatures.count,
                'fillets': self.root_comp.features.filletFeatures.count,
                'chamfers': self.root_comp.features.chamferFeatures.count,
                'shells': self.root_comp.features.shellFeatures.count,
                'patterns': self.root_comp.features.rectangularPatternFeatures.count +
                           self.root_comp.features.circularPatternFeatures.count
            }
            return features
        except:
            return {}
    
    def get_material(self):
        """Get material name if assigned"""
        try:
            for body in self.root_comp.bRepBodies:
                if body.material:
                    return body.material.name
            return "No material assigned"
        except:
            return "Unknown"
    
    def get_surface_area(self):
        """Get total surface area in cm²"""
        try:
            area_cm2 = 0
            
            for body in self.root_comp.bRepBodies:
                props = body.physicalProperties
                area_cm2 += props.area * 10000  # Convert m² to cm²
            
            return round(area_cm2, 2)
        except:
            return 0.0
    
    def get_stress_points(self):
        """
        Identify potential stress concentration points
        This is a simplified version - real implementation would use FEA
        """
        # For now, return sharp corners and small fillets
        # In future, integrate with Fusion's FEA API
        return {
            'sharp_corners': [],
            'thin_sections': [],
            'high_stress_regions': []
        }
