# most code modified from Arjan codes github library:
# https://github.com/ArjanCodes/2021-command-undo-redo/blob/main/LICENSE
# TODO mention it in case of implementation (MIT LICENSE)
from dataclasses import dataclass, field
from typing import List

import warnings
from ._workflow import Workflow, _layer_name_or_value
from napari import Viewer

@dataclass
class Undo_redo_controller:
    """
    This is a class that performs Actions that are handed to it and keeps
    track of which Actions were performed. Undo and redo can then be called with
    this class, reverting the changes made to a workflow

    Parameters
    ----------
    undo_stack: list[Action]
        List of Actions for which the undo function will be executed if 
        Undo_redo_controller.undo() is called

    redo_stack: list[Action]
        List of Actions for which the redo function will be executed if 
        Undo_redo_controller.undo() is called

    freeze_stacks: bool
        Actions can be performed on the workflow but undo and redo stacks
        remain unchanged when freeze_stacks = True
    """
    workflow: Workflow
    viewer: Viewer
    undo_stack: List[Workflow] = field(default_factory = list)
    redo_stack: List[Workflow] = field(default_factory = list)
    freeze_stacks: bool = False
    

    def execute(self,action) -> None:
        if not self.freeze_stacks:
            # we only want to update the undo stack if the workflow 
            # actually changes (otherwise undo won't function properly)

            if len(self.undo_stack) == 0: 
                self.undo_stack.append(
                    copy_workflow_state(self.workflow)
                    )
                self.redo_stack.clear()
                action.execute()
                return
            if len(self.workflow._tasks.keys()) != len(self.undo_stack[-1]._tasks.keys()):
                self.undo_stack.append(
                    copy_workflow_state(self.workflow)
                )
                self.redo_stack.clear()
                action.execute()
                return

            # workaround for situation where input image does not match 
            # any layer in viewer
            workflows_differ = False
            try:
                workflows_differ = (self.workflow._tasks != (self.undo_stack[-1])._tasks)
            except ValueError:
                warnings.warn("Cannot determine layer from image - Undo functionality impaired")
                
            if workflows_differ:  
                self.undo_stack.append(
                    copy_workflow_state(self.workflow)
                )
                self.redo_stack.clear()
        action.execute()

    def undo(self) -> Workflow:
        if not self.undo_stack:
            return
        undone_workflow = self.undo_stack.pop()
        if not self.freeze_stacks:
            self.redo_stack.append(
                copy_workflow_state(self.workflow)
            )
        return undone_workflow

    def redo(self) -> Workflow:
        if not self.redo_stack:
            return
        redone_workflow = self.redo_stack.pop()
        if not self.freeze_stacks:
            self.undo_stack.append(
                copy_workflow_state(self.workflow)
            )
        return redone_workflow

    def compare_workflows(workflow_1, workflow_2):
        tasks_1 = workflow_1._tasks
        tasks_2 = workflow_2._tasks

        if set(tasks_1.keys()) != set(tasks_2.keys()):
            return False
        for (k1,v1),(k2,v2) in zip(sorted(tasks_1.items()),sorted(tasks_2.items())):
            if _layer_name_or_value(v1) != _layer_name_or_value(v2):
                return False
        return True
    
def copy_workflow_state (workflow: Workflow) -> Workflow:
    """
    Returns a new Workflow object with identical parameters but not 
    including any input images
    """
    workflow_state = Workflow()
    for key, value in workflow._tasks.items():
        if callable(value[0]): 
            workflow_state.set(key, value)

    return workflow_state

