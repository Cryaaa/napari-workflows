from ._workflow import Workflow, _layer_name_or_value
from napari import Viewer
from numpy import ndarray

class Update_workflow_step:
    """
    Action which updates a given workflow step based on a target layer and function
    including args and kwargs.

    Parameters
    ----------
    """
    def __init__(self, workflow: Workflow, viewer: Viewer, target_layer, function, *args, **kwargs) -> None:
        self.workflow = workflow
        self.viewer = viewer
        self.target_layer = target_layer
        self.function = function
        self.args = args
        self.kwargs = kwargs

        try:
            self.old_task = workflow._tasks[target_layer.name]
        except KeyError:
            self.old_task = None

    def execute(self):
        # basically what the update function was doing before
        corrected_kwargs = {k:v for k,v in self.kwargs.items() if not ((isinstance(v, Viewer)) or (k == 'viewer'))}
        args = list(self.args)
        for i in range(len(args)):
            args[i] = _layer_name_or_value(args[i], self.viewer)
        if isinstance(args[-1], Viewer):
            args = args[:-1]
        args = tuple(args)
        self.workflow.set(self.target_layer.name, self.function, *args, **corrected_kwargs)

        # plus the remove zombies function
        kill_zombies(self.viewer,self.workflow)

    def __str__(self) -> str:
        """
        Return useful information about action for debugging purposes
        """
        if not self.old_task:
            add_change = 'added'
        else:
            add_change = 'changed'
        string = f'Function: {self.function.__name__} {add_change}\n'
        string+= f'    args: {[arg for arg in self.args if not isinstance(arg,ndarray)]}\n'
        string+= f'    kwargs: {self.kwargs}\n'
        string+= f'    layer name: {self.target_layer.name}\n'
        string+= f'    zombies: {self.removed_layers.keys()}\n'

        return string

class Remove_zombies:
    # TODO Docstring
    def __init__(self, workflow: Workflow, viewer = Viewer) -> None:
        self.workflow = workflow
        self.viewer = viewer

    def execute(self):
        kill_zombies(self.viewer,self.workflow)

class Layer_removed:
    # TODO Docstring
    def __init__(self, workflow: Workflow, name: str) -> None:
        self.workflow = workflow
        self.name = name
        try:
            self.old_task = workflow._tasks[name]
        except KeyError:
            self.old_task = None

    def execute(self) -> None:
        self.workflow.remove(self.name)

def kill_zombies(viewer, workflow):
    layer_names = [layer.name for layer in viewer.layers]
    workflow.remove_all_except(layer_names)

# old update func for reference:
import napari
METADATA_WORKFLOW_VALID_KEY = "workflow_valid"
def update(self, target_layer, function, *args, **kwargs):
    """
    Update the task representing a given layer in the stored workflow by providing
    the function and parameters that generated the data in the layer.

    Other layers that were produced from the data stored in this layer are invalidated.

    Parameters
    ----------
    target_layer: napari.layers.Layer
    function: callable
    args: list
    kwargs: dict
    """
    args = list(args)
    for i in range(len(args)):
        args[i] = _layer_name_or_value(args[i], self.viewer)
    if isinstance(args[-1], napari.Viewer):
        args = args[:-1]
    args = tuple(args)

    self.workflow.set(target_layer.name, function, *args, **kwargs)

    self.remove_zombies()

    # set result valid
    target_layer.metadata[METADATA_WORKFLOW_VALID_KEY] = True
    self.invalidate(self.workflow.followers_of(target_layer.name))