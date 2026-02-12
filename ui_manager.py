"""
UI Manager - Creates and manages the Fusion 360 UI panel
"""

import adsk.core


class UIManager:
    """
    Manages the UI elements for the InteliCAD add-in
    """
    
    PANEL_ID = 'InteliCADPanel'
    COMMAND_ID = 'InteliCADCommand'
    
    def __init__(self, ui):
        self.ui = ui
    
    def create_panel(self):
        """
        Create the add-in panel in Fusion 360
        """
        try:
            # Get the ADD-INS panel
            all_panels = self.ui.allToolbarPanels
            add_ins_panel = all_panels.itemById('SolidScriptsAddinsPanel')
            
            if not add_ins_panel:
                self.ui.messageBox('ADD-INS panel not found')
                return
            
            # Check if panel already exists
            existing_panel = all_panels.itemById(self.PANEL_ID)
            if existing_panel:
                existing_panel.deleteMe()
            
            # Create our panel
            panel = add_ins_panel.controls.addDropDown(
                'InteliCAD',
                '',
                self.PANEL_ID
            )
            
            # Add status indicator
            # Note: Fusion doesn't support dynamic text in panels easily
            # For now, just create the panel
            
        except Exception as e:
            self.ui.messageBox(f'Failed to create panel: {e}')
    
    def cleanup(self):
        """
        Remove the panel when add-in stops
        """
        try:
            all_panels = self.ui.allToolbarPanels
            panel = all_panels.itemById(self.PANEL_ID)
            if panel:
                panel.deleteMe()
        except:
            pass
