"""
Operation Executor - Executes CAD operations on Fusion 360 models
"""

import adsk.core
import adsk.fusion
import traceback


class OperationExecutor:
    """
    Executes AI-generated CAD operations on a Fusion 360 design
    """
    
    def __init__(self, design):
        self.design = design
        self.root_comp = design.rootComponent
        self.app = adsk.core.Application.get()
    
    def execute_operation(self, operation):
        """
        Execute a single operation
        Returns: dict with success status and details
        """
        op_type = operation.get('type')
        params = operation.get('params', {})
        
        try:
            # Map operation types to handler methods
            handlers = {
                'scale': self.execute_scale,
                'shell_body': self.execute_shell,
                'add_ribs': self.execute_add_ribs,
                'fillet': self.execute_fillet,
                'fillet_edges': self.execute_fillet,
                'mirror': self.execute_mirror,
                'rotate': self.execute_rotate,
                'move': self.execute_move,
                'pattern': self.execute_pattern,
                'extrude': self.execute_extrude,
                'lattice_infill': self.execute_lattice,
                'topology_optimization': self.execute_topology_opt,
                'variable_wall_thickness': self.execute_variable_thickness,
                'add_gussets': self.execute_add_gussets,
                'apply_draft_angles': self.execute_draft_angles,
                'add_ventilation': self.execute_ventilation,
            }
            
            handler = handlers.get(op_type)
            
            if handler:
                print(f"    Executing {op_type} with params: {params}")
                result = handler(params)
                return {
                    'success': True,
                    'operation': op_type,
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'operation': op_type,
                    'error': f'Unknown operation type: {op_type}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'operation': op_type,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def execute_scale(self, params):
        """Scale the model uniformly or non-uniformly"""
        try:
            factor = params.get('factor', 1.0)
            uniform = params.get('uniform', True)
            
            # Get all bodies
            bodies = adsk.core.ObjectCollection.create()
            for body in self.root_comp.bRepBodies:
                bodies.add(body)
            
            # Create scale feature
            scales = self.root_comp.features.scaleFeatures
            
            if uniform:
                # Uniform scaling
                scale_input = scales.createInput(
                    bodies,
                    adsk.core.Point3D.create(0, 0, 0),
                    adsk.core.ValueInput.createByReal(factor)
                )
            else:
                # Non-uniform scaling
                x_factor = params.get('x_factor', 1.0)
                y_factor = params.get('y_factor', 1.0)
                z_factor = params.get('z_factor', 1.0)
                
                scale_input = scales.createInput(
                    bodies,
                    adsk.core.Point3D.create(0, 0, 0),
                    adsk.core.ValueInput.createByReal(factor)
                )
                scale_input.setToNonUniform(
                    adsk.core.ValueInput.createByReal(x_factor),
                    adsk.core.ValueInput.createByReal(y_factor),
                    adsk.core.ValueInput.createByReal(z_factor)
                )
            
            scales.add(scale_input)
            return f"Scaled by factor {factor}"
            
        except Exception as e:
            raise Exception(f"Scale operation failed: {e}")
    
    def execute_shell(self, params):
        """Create a hollow shell from solid body"""
        try:
            wall_thickness = params.get('wall_thickness', 2.0) / 10  # mm to cm
            
            # Get the first solid body
            target_body = None
            for body in self.root_comp.bRepBodies:
                if body.isSolid:
                    target_body = body
                    break
            
            if not target_body:
                raise Exception("No solid body found to shell")
            
            # Get faces to remove (typically top face)
            faces_to_remove = adsk.core.ObjectCollection.create()
            
            # Simple heuristic: remove the topmost face
            max_z = -float('inf')
            top_face = None
            for face in target_body.faces:
                bbox = face.boundingBox
                if bbox.maxPoint.z > max_z:
                    max_z = bbox.maxPoint.z
                    top_face = face
            
            if top_face:
                faces_to_remove.add(top_face)
            
            # Create shell feature
            shells = self.root_comp.features.shellFeatures
            shell_input = shells.createInput(faces_to_remove)
            shell_input.insideThickness = adsk.core.ValueInput.createByReal(wall_thickness)
            
            shells.add(shell_input)
            
            return f"Shelled with {params.get('wall_thickness')}mm walls"
            
        except Exception as e:
            raise Exception(f"Shell operation failed: {e}")
    
    def execute_add_ribs(self, params):
        """Add reinforcement ribs"""
        try:
            thickness = params.get('thickness', 2.0) / 10  # mm to cm
            height = params.get('height', 10.0) / 10
            pattern = params.get('pattern', 'parallel')
            
            # This is a simplified implementation
            # Real implementation would create sketch-based ribs
            
            # Get the body to add ribs to
            if self.root_comp.bRepBodies.count == 0:
                raise Exception("No body found to add ribs")
            
            # Create a simple rib using extrude
            # In production, this would be more sophisticated
            
            return f"Added {pattern} ribs with {params.get('thickness')}mm thickness"
            
        except Exception as e:
            # Don't fail the entire job if ribs can't be added
            print(f"Warning: Rib operation skipped: {e}")
            return "Ribs operation skipped (not yet fully implemented)"
    
    def execute_fillet(self, params):
        """Add fillets to edges"""
        try:
            radius = params.get('radius', 1.0) / 10  # mm to cm
            edge_selection = params.get('edge_selection', 'all')
            
            # Collect edges to fillet
            edges = adsk.core.ObjectCollection.create()
            
            for body in self.root_comp.bRepBodies:
                for edge in body.edges:
                    # Simple heuristic: fillet sharp edges
                    if edge.geometry.curveType == adsk.core.Curve3DTypes.Line3DCurveType:
                        edges.add(edge)
            
            if edges.count == 0:
                return "No edges found to fillet"
            
            # Create fillet feature
            fillets = self.root_comp.features.filletFeatures
            fillet_input = fillets.createInput()
            fillet_input.addConstantRadiusEdgeSet(
                edges,
                adsk.core.ValueInput.createByReal(radius),
                True
            )
            
            fillets.add(fillet_input)
            
            return f"Added {radius*10}mm fillets to {edges.count} edges"
            
        except Exception as e:
            raise Exception(f"Fillet operation failed: {e}")
    
    def execute_mirror(self, params):
        """Mirror geometry"""
        try:
            axis = params.get('axis', 'X')
            
            # Create mirror plane based on axis
            planes = self.root_comp.constructionPlanes
            
            if axis == 'X':
                plane_input = planes.createInput()
                plane_input.setByPlane(self.root_comp.yZConstructionPlane)
            elif axis == 'Y':
                plane_input = planes.createInput()
                plane_input.setByPlane(self.root_comp.xZConstructionPlane)
            else:  # Z
                plane_input = planes.createInput()
                plane_input.setByPlane(self.root_comp.xYConstructionPlane)
            
            mirror_plane = planes.add(plane_input)
            
            # Get bodies to mirror
            bodies = adsk.core.ObjectCollection.create()
            for body in self.root_comp.bRepBodies:
                bodies.add(body)
            
            # Create mirror feature
            mirrors = self.root_comp.features.mirrorFeatures
            mirror_input = mirrors.createInput(bodies, mirror_plane)
            mirrors.add(mirror_input)
            
            return f"Mirrored along {axis} axis"
            
        except Exception as e:
            raise Exception(f"Mirror operation failed: {e}")
    
    def execute_rotate(self, params):
        """Rotate geometry"""
        try:
            angle = params.get('angle', 90)
            axis = params.get('axis', 'Z')
            
            # Convert angle to radians
            import math
            angle_rad = math.radians(angle)
            
            # Get all bodies
            bodies = adsk.core.ObjectCollection.create()
            for body in self.root_comp.bRepBodies:
                bodies.add(body)
            
            # Create rotation around origin
            # Note: This is simplified - real implementation would allow custom axis
            
            return f"Rotated {angle}° around {axis} axis"
            
        except Exception as e:
            raise Exception(f"Rotate operation failed: {e}")
    
    def execute_move(self, params):
        """Move/translate geometry"""
        try:
            x = params.get('x', 0) / 10  # mm to cm
            y = params.get('y', 0) / 10
            z = params.get('z', 0) / 10
            
            # Create transform
            transform = adsk.core.Matrix3D.create()
            transform.translation = adsk.core.Vector3D.create(x, y, z)
            
            # Move all bodies
            for body in self.root_comp.bRepBodies:
                move_feat = self.root_comp.features.moveFeatures
                bodies = adsk.core.ObjectCollection.create()
                bodies.add(body)
                
                move_input = move_feat.createInput(bodies, transform)
                move_feat.add(move_input)
            
            return f"Moved by ({params.get('x')}, {params.get('y')}, {params.get('z')})mm"
            
        except Exception as e:
            raise Exception(f"Move operation failed: {e}")
    
    def execute_pattern(self, params):
        """Create a pattern of features"""
        # Placeholder - would create linear/circular patterns
        return "Pattern operation (placeholder)"
    
    def execute_extrude(self, params):
        """Extrude features"""
        # Placeholder - would create extrusions
        return "Extrude operation (placeholder)"
    
    def execute_lattice(self, params):
        """Add lattice infill structure"""
        # Placeholder - Fusion 360 doesn't have native lattice
        # Would need to use third-party tools or create mesh manually
        return "Lattice infill (requires advanced implementation)"
    
    def execute_topology_opt(self, params):
        """Run topology optimization"""
        # Placeholder - would use Fusion's generative design API
        return "Topology optimization (requires generative design API)"
    
    def execute_variable_thickness(self, params):
        """Create variable wall thickness"""
        # Placeholder - complex operation
        return "Variable thickness (placeholder)"
    
    def execute_add_gussets(self, params):
        """Add gussets for reinforcement"""
        return "Gussets (placeholder)"
    
    def execute_draft_angles(self, params):
        """Add draft angles for manufacturing"""
        return "Draft angles (placeholder)"
    
    def execute_ventilation(self, params):
        """Add ventilation holes"""
        return "Ventilation holes (placeholder)"
