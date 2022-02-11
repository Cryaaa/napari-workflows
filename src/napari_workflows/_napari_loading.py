from inspect import Signature, signature
from functools import partial
from napari_workflows import Workflow
from magicgui.widgets import FunctionGui
from functools import wraps

class flexible_gui(FunctionGui):
    def __init__(self,function,param_options):
        super().__init__(
          function,
          call_button=True,
          layout='vertical',
          #auto_call=True,
          param_options=param_options
        )

def make_flexible_gui(func, param_options, viewer):
    gui = None

    from napari.types import ImageData, LabelsData
    import inspect
    sig = inspect.signature(func)

    @wraps(func)
    def worker_func(*iargs, **ikwargs):
        data = func(*iargs, **ikwargs)
        if data is None:
            return None

        target_layer = None

        if sig.return_annotation in [ImageData, "napari.types.ImageData", LabelsData, "napari.types.LabelsData"]:
            op_name = func.__name__
            new_name = f"{op_name} result"

            # we now search for a layer that has -this- magicgui attached to it
            try:
                # look for an existing layer
                target_layer = next(x for x in viewer.layers if x.source.widget is gui)
                target_layer.data = data
                target_layer.name = new_name
                # layer.translate = translate
            except StopIteration:
                # otherwise create a new one
                from napari.layers._source import layer_source
                with layer_source(widget=gui):
                    if sig.return_annotation in [ImageData, "napari.types.ImageData"]:
                        target_layer = viewer.add_image(data, name=new_name)
                    elif sig.return_annotation in [LabelsData, "napari.types.LabelsData"]:
                        target_layer = viewer.add_labels(data, name=new_name)

        if target_layer is not None:
            # update the workflow manager in case it's installed
            try:
                from napari_workflows import WorkflowManager
                workflow_manager = WorkflowManager.install(viewer)
                workflow_manager.update(target_layer, func, *iargs, **ikwargs)
            except ImportError:
                pass

            return None
        else:
            return data

    gui = flexible_gui(worker_func, param_options)
    return gui

def signature_w_kwargs_from_function(function, arg_vals: list) -> Signature:
    """
    Returns a new signature for a function in which the default values are replaced
    with the arguments given in arg_vals

    Parameters
    ----------
    function: 
        input function to generate new signature

    arg_vals: list
        list of arguments to replace defaults in signature
    """

    # getting the keywords corresponding to the values
    keyword_list = list(signature(function).parameters.keys())

    # creating the kwargs dict
    kw_dict = {}
    for kw, val in zip(keyword_list, arg_vals):
        kw_dict[kw] = val
        
    possible_input_image_names = ['image',
                                  'label_image',
                                  'binary_image'
                                 ]
    for name in possible_input_image_names:
        try:
            kw_dict.pop(name) # we are making an assumption that the input will aways be this
        except KeyError:
            pass

    
    sig = signature(partial(function, **kw_dict))
    
    return sig

def wf_steps_with_root_as_input(workflow):
    """
    Returns a list of workflow steps that have root images as an input

    Parameters
    ----------
    workflow: 
        napari_workflows Workflow class
    """
    roots = workflow.roots()
    wf_step_with_rootinput = []
    for result, task in workflow._tasks.items():
            for source in task:
                if isinstance(source, str):
                    if source in roots:
                        wf_step_with_rootinput.append(result)
    return wf_step_with_rootinput

def old_wf_names_to_new_mapping(workflow: Workflow)-> dict:
    """
    Returns a dictionary mapping old workflow step names to new ones

    Parameters
    ----------
    workflow: 
        napari_workflows Workflow class
    """
    mapping = {}
    for old_key, content in workflow._tasks.items():
        func = content[0]
        new_name = 'Result of ' + func.__name__
        mapping[old_key] = new_name
    
    return mapping
        
def get_parameter_options(workflow, wf_step: str, viewer, old_wf_names_to_new_mapping = None):
    """
    Returns a parameter options that can be handed to the flexible_gui class in order to
    only allow the correct dropdown options

    Parameters
    ----------
    workflow: 
        napari_workflows Workflow class

    wf_step: str
        Name of workflow step for which the parameter options should be generated
    
    viewer:
        napari Viewer instance

    old_wf_names_to_new_mapping:
        dictionary mapping old workflow step names to new ones
    """

    func = workflow._tasks[wf_step][0]
    args = workflow._tasks[wf_step][1:]

    keyword_list = list(signature(func).parameters.keys())
    image_keywords = [(key,value) for key, value in zip(keyword_list,args) if isinstance(value, str)]
    image_names = [key for key, value in zip(keyword_list,args) if isinstance(value, str)]

    if old_wf_names_to_new_mapping is None:
        conversion_dict = {name: name for name in image_names}
    else:
        conversion_dict = old_wf_names_to_new_mapping

    param_options = {}
    for key, name in image_keywords:
        param_options[key] = {'choices': [viewer.layers[conversion_dict[name]].data]}

    return param_options