"""
Docs

Developers:
James Briggs

Description:
This module is used to automatically generate HTML-based documentation for
Python scripts with NumPy/SciPy format docstrings and correct code and syntax
conventions followed throughout.
Please see NumPy/SciPy docstrings formatting guidance here:
https://numpydoc.readthedocs.io/en/latest/format.html
"""

import os
import re
import requests

def extract_params(text):
    """
    Function used to extract parameters from a function docstring.

    Parameters
    ----------
    text : str
        Parameters section of a function docstring. For example what you are
        reading right now is within the parameters section of the extract_params
        docstring.

    Returns
    -------
    params : dict
        Dictionary containing all parameters found and their descriptions,
        datatypes, and whether they are optional or not.
    """
    # this will match a parameter name, type, description (and name of following param)
    param_re = re.compile(r"(?sm)\w+ : [^:]+")
    # initialise parameter dictionary
    params = {}
    while True:
        new_param = param_re.search(text)
        #print(new_param)
        if new_param is None:
            # if no parameters have been found, break from loop
            break
        # extract text
        new_param = new_param.group()

        # split by newline character and remove final line (the name of the following param)
        new_param = new_param.split('\n')[:-1]

        # first line is param name and description, get both
        name, dtype = new_param[0].split(":")

        # formatting description
        desc = "\n".join(new_param[1:])
        desc = re.sub(r"\s+", " ", desc)

        # check if a parameter is optional
        if 'optional' in dtype:
            dtype = dtype.split(",")[0]
            optional = True
        else:
            optional = False

        # add parameter details to params dictionary
        params[name.strip()] = {
            'dtype': dtype.strip(),
            'description': desc.strip(),
            'optional': optional
        }

        text = text.replace("\n".join(new_param), "")

    return params


def extract_functions(code):
    """
    Function used to extract functions from Python code.

    Parameters
    ----------
    code : str
        Python code containing functions to be extracted.

    Returns
    -------
    funcs : dict
        Dictionary containing function names, descriptions, and parameters.
        These parameters are also dictionaries containing their own metadata.

    """
    funcs = {}
    # create compiled regex for finding functions and their following docstrings
    func_re = re.compile(r"(?m)def [\w\d_]+\([\w\d\n\/_=,.'\" ]+\):\s+\"{3}[^#]+\"{3}")

    # build list of functions
    func_list = func_re.findall(code)

    # iterate through list, extracting key information for each function
    for func in func_list:
        # get function name
        name = re.search(r"def [\w\d_]+\(", func).group()
        name = name.replace("def ", "").replace("(", "").strip()

        # pull out function docstring in between triple quotes block
        desc = re.search(r"(?s)\"{3}.*\"", func).group()
        # split the docstring into description and parameters
        desc, params = desc.split("Parameters\n")
        # remove excessive whitespace from description
        desc = re.sub(r"\s+", " ", desc.replace('"""', "")).strip()

        # remove Returns section from parameters
        params = params.split("Returns\n")[0]
        # extract parameter details from parameters section
        params = extract_params(params)

        # add function to functions dictionary
        funcs[name] = {
            'description': desc,
            'parameters': params
        }
    return funcs


def extract_module(code):
    """
    Function used to extract the top block quote containing key information
    on the Python script. Including module name, developers, and description.

    Parameters
    ----------
    code : str
        Python code containing the module description in the first block quote.
        Should containing module name first, developers on a line following
        'Developers:', and description last, beginning on a line following
        'Description:'.

    Returns
    -------
    name : str
        Module name.
    devs : str
        Name of developers.
    desc : str
        Description of the module.
    """

    # extract the first block quote
    text = re.search(r"(?sm)^\"{3}.*^\"{3}", code).group()
    # pull module name from the second line
    name = text.split("\n")[1].strip()
    # pull Developers
    devs = re.search(r"Developers:\n.*", text).group()
    # remove 'Developers:' line so we just have names
    devs = devs.replace("Developers:\n", "").strip()
    # finally split text by 'Description:' and take the description (index 1)
    desc = text.split("Description:\n")[1].replace('"""', "").strip()
    # return all extracted module metaata
    return name, devs, desc


def functions_html(funcs):
    """
    Function used to build HTML code from a dictionary of functions.

    Parameters
    ----------
    funcs : dict
        Dictionary containing functions. Must be function name as dictionary
        key, function parameters within 'parameters', and function description
        within 'description'. Another dictionary for each function parameter
        should be included for each paramter within 'parameters', this will
        contain parameter description, datatype, and whether it is an optional
        parameter or not.

    Returns
    -------
    html : str
        The HTML code built.
    """
    html = """
        <h2>Functions</h2>
        <br>
        <ul>
    """  # initialise html object

    # iterate through and add function sections
    for name in funcs:
        html += f"""
        <li class="list-group-item" id="func_{name}">
          <h4>{name}</h4>
          <kbd>{name}({", ".join([param for param in funcs[name]['parameters']])})</kbd><br><br>
          <p>
            {funcs[name]['description']}
          </p>
        """
        if len(funcs[name]['parameters']) > 0:
            html += f"""
          <!-- Parameters table for {name} -->
          <table class="table table-hover">
            <tbody>
            """
            for param in funcs[name]['parameters']:
                # check if the parameter is optional
                if funcs[name]['parameters'][param]['optional']:
                    # if so, we put 'emphasis' tags and an apostrophy around
                    # the parameter name in the table
                    opt1 = "<em>"
                    opt2 = "*</em>"
                else:
                    # otherwise, nothing is needed
                    opt1 = opt2 = ""
                html += f"""
              <tr>
                <th scope="row">{opt1}{param}{opt2}</th>
                <td>
                  {funcs[name]['parameters'][param]['description']}
                </td>
              </tr>
                """
            html += f"""
            </tbody>
          </table>
            """
        html += f"""
        </li>
        <br>
        """

    html += """
        </ul>
    """  # end Functions section

    return html


def build_navbar(to_include, docs_dir='./Documentation'):
    """
    Function for building a navigation bar 'navbar.js'. This will be saved to
    the templates folder within the docs directory.
    
    Parameters
    ----------
    to_include : list
        List of scripts or classes to add to the navbar. These should be given
        in the 'module' name format given to the DocsBuilder class so that
        the links are built correctly.
    docs_dir : str, optional
        The local/global path to the documentation directory. This should
        contain a 'templates' folder which would contain Bootstrap codes and
        this navbar. If it does not exist this function will add the folder.
    
    Returns
    -------
    None.
    """

    raise ValueError("'build_navbar' script is not complete.")
    # !!! TODO make the navbar code here
    navbar = ""

    # now save to templates within the docs directory
    output(navbar, 'navbar,js', os.path.join(docs_dir, '/templates'))


def build_page(module, devs, desc, classes="", funcs="", submodule=""):
    """
    Function for building HTML docs using extracted data.

    Parameters
    ----------
    module : str
        String containing the module name.
    devs : str
        String containing the names of script developers.
    desc : str
        String describing the module.
    classes : dict, optional
        Dictionary containing classes and their description, code, functions,
        and variables. The default is "".
    funcs = dict, optional
        Dictionary containing functions and their descriptions and parameters.
    submodule = str, optional
        String containing the submodule name, if within a submodule, eg class.

    Returns
    -------
    None.
    """
    # assign fullpath as list of module and (optionally) submodule
    if submodule != "":
        fullpath = [module, submodule]
    else:
        fullpath = [module]

    html = f"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
<meta name="description" content="{fullpath[-1]} documentation">
<meta name="author" content="{devs}">

<title>{fullpath[-1]} Documentation</title>

<link href="templates/bootstrap.min.css" rel="stylesheet">

</head>

<body>

<!-- Navigation -->
<script src="templates/navbar.js"></script>

<!-- Page Content -->
<div class="container">
<div class="row">
  <div class="col-lg-12 text-left">

    <h1 class="mt-5">{fullpath[-1]}</h1>
    <p class="lead">
      {desc}
    </p>

    <br>

    <!-- Breadcrumb Navigation -->
    <nav aria-label="breadcrumb">
      <ol class="breadcrumb">
        <li class="breadcrumb-item active"><a href="../readme.html">Documentation</a></li>
    """
    for i, part in enumerate(fullpath):
        if i+1 != len(fullpath):
            # add in a hypterlink
            html += f"""
        <li class="breadcrumb-item active"><a href="{part.lower().replace(" ", "_")}.html">{part}</a></li>
            """
        else:
            # otherwise, no hyperlink as is current page
            html += f"""
        <li class="breadcrumb-item" aria-current="page">{part}</li>
            """
    html += """
      </ol>
    </nav>

    <br>

    """

    # if length of classes is not zero
    if len(classes) > 0:
        # add class section start
        html += """
    <h2>Classes</h2>
    <div class="row">
      <!-- Class Buttons -->
      <div class="col-4">
        <div class="list-group" id="list-mod" role="tablist">
        """
        # iterate through and add buttons/links
        for name in classes:
            html += f"""
          <a class="list-group-item list-group-item-action" id="label_{name}" data-toggle="list" href="#card_{name}" role="tab" aria-controls="home">{name}</a>
            """
        # add end of button/links section
        html += """
        </div>
      </div>
      <!-- Class Button Contents -->
      <div class="col-8">
        <div class="tab-content" id="nav-tabContent">
        """
        # iterate through and add button contents
        for name in classes:
            html += f"""
          <div class="tab-pane fade" id="card_{name}" role="tabpanel" aria-labelledby="label_{name}">
            <p>
              {classes[name]['description']}
            </p>
            <p>
              <a href="{module.lower().replace(" ", "_")}.{name}.html">Click here for documentation</a>
            </p>
          </div>
            """
        # end class section
        html += f"""
        </div>
      </div>
    </div>

    <br>
        """

    # add functions sections if functions exist
    if len(funcs) > 0:
        html += functions_html(funcs)

    # add end of html
    html += """
  </div>
</div>
</div>
<br>

<!-- Bootstrap core JavaScript -->
<script src="templates/jquery.min.js"></script>
<script src="templates/bootstrap.bundle.min.js"></script>

</body>

</html>
    """

    return html


def output(code, filename, path="./Documentation", overwrite=False):
    """
    Function to control saving of HTML files.

    Parameters
    ----------
    path : str, optional
        String containing the local/global filepath to the Documentation
        directory. The HTML files will be saved here.
        The default is './Documentation'.
    overwrite : Boolean, optional
        True/False determining whether pre-existing files will be
        overwritten without warning. If False then overwrite will still be
        possible but a warning will appear if there are any pre-existing
        files, which will confirm the user's intention in overwritting or
        otherwise.

    Returns
    -------
    None.
    """

    # check if the filename given already has an extension
    if any(['.html', '.css', '.js']) not in filename:
        # if no extension given, we assume it is an html file
        filename += '.html'

    # if output directory does not already exist, make it
    if not os.path.isdir(path):
        os.makedirs(path)

    # check if file exists and warn user if so (unless overwrite=True)
    if os.path.exists(os.path.join(path, filename)) or not overwrite:
        overwrite = input(f"Warning: '{filename}' already exists, do you "
                           "want to overwrite? (Y/N)\n>>> ")
        if overwrite.lower()[0] == 'y':
            pass
        else:
            # otherwise we just preappend 'auto' to the filename
            filename = f"auto_{filename}"

    # save code to file
    with open(os.path.join(path, filename), 'w') as fp:
        fp.write(code)
        print(f"{filename.split('.')[-1].upper()} file saved to '{fp}'.")


def bootstrap_download(docs_dir):
    """
    Function used for downloading Bootstrap files. These are downloaded from
    this projects GitHub repo.
    
    Parameters
    ----------
    docs_dir : str
        The local/global path to the documentation directory.
    
    Returns
    -------
    None.
    """
    
    # initialise Bootstrap components directory
    components = {
            'css': 'bootstrap.min.css',
            'js': 'bootstrap.bundle.min.js',
            'jquery': 'jquery.min.js'
        }

    # get source address
    src = "https://github.com/jamescalam/autodocs/Documentation/templates"

    for part in components:
        # get the web address for each part
        part_src = os.path.join(src, components[part][0])
        # download the code and store in components dictionary
        code = requests.get(part_src).text
        # now save the component to file (in the documentation templates dir)
        output(code, components[part][0],
               path=os.path.join(docs_dir, '/templates'))


class DocsBuilder:
    """
    Class used for automatically generating HTML-based documentation from Python
    code. Note that the Python code must be written correctly and commented.
    Function docstrings must also follow NumPy/SciPy docstring formatting
    conventions.
    """
    def __init__(self, docs_dir='./Documentation', offline=False):
        """
        Initialise DocsBuilder class. Checks the given documentation directory
        for Bootstrap templates, if not found will download from <TK webpage>
        here. Also compiles useful Regular Expressions (TK add class finder to
        it's own function).

        Parameters
        ----------
        docs_dir : str
            The local/global path to the documentation directory.

        Returns
        -------
        None.
        """

        # check if bootstrap css exists
        if not os.path.exists(os.path.join(docs_dir, '/templates/')):
            # if it does not exist, create one
            os.mkdir(docs_dir)
            print(f"Added documentation directory:\\n'{docs_dir}'.")
        # check if the templates directory exists
        if not os.path.isdir(os.path.join(docs_dir, '/templates')):
            # if does not exist, create it
            os.mkdir(os.path.join(docs_dir, '/templates'))
            print("Added templates directory:\n"
                  f"'{os.path.join(docs_dir, '/templates')}'.")
            
        # compiled regex for finding import libraries
        self.libs_re = re.compile(r"")
        # create compiled regex for finding classes and all that they contain (final character must be removed though)
        self.class_re = re.compile(r"(?sm)class [\w\d_]+:.*(^\n\w)")
        # if we don't find any with above, we can try with this for class at end of file
        self.class_end_re = re.compile(r"(?sm)class [\w\d_]+:.*")

    def extract(self, code):
        """
        Function for extracting imported libraries/modules, global variables,
        functions and classes.

        Parameters
        ----------
        code : str
            String containing the Python code to be documented.

        Returns
        -------
        None.
        """

        # pull module metadata
        self.module, self.devs, self.desc = extract_module(code)

        # !!! TODO
        self.libs = self.libs_re.findall(code)  # find all imported libraries

        # !!! TODO
        self.vars = self.vars_re.findall(code)  # find all global libraries

        # initialise classes dictionary
        self.classes = {}
        # find all classes, this must be done in a loop for multiple classes
        while True:
            new_class = self.class_re.search(code)  # find a class
            # check if we have found any new classes
            if new_class is None:
                # see if class at end
                new_class = self.class_end_re.search(code)
                if new_class is None:
                    # if no classes anywhere, break the loop
                    break
            code = code.replace(new_class.group()[:-1], "")  # remove from code
            # get class name
            name = re.compile(r"class .*:").search(new_class.group()).group()  # find class first line definition
            # clean class definition so that we only have class name
            name = name.replace("class ", "").replace(":", "")
            # initialise description
            desc = ""

            # check class has DESCRIPTION
            if re.compile(r"class .*:[\n\s]+\"{3}[\w\d\s_=,.:{}'<>\[\]-]+\"{3}").search(new_class.group()):
                # if so, get class description
                desc = re.compile(r"class .*:[\n\s]+\"{3}[\w\d\s_=,.:{}'<>\[\]-]+\"{3}").search(new_class.group()).group()
                # remove class definition and triple quotes from desc
                desc = re.sub(r"class .*:", "", desc).replace('"""', "")
                # remove excessive whitespace
                desc = re.sub(r"\s+", " ", desc)

            # extract functions contained within the class
            class_funcs = extract_functions(new_class.group()[:-1])

            self.classes[name] = {
                'description': desc,
                'code': new_class.group()[:-1],
                'funcs': class_funcs
            }

        self.funcs = extract_functions(code)  # find all functions
        #code = self.funcs_re.sub("", code)  # remove from code


    def build(self, path="./Documentation", overwrite=False):
        """
        Function for building HTML docs using extracted data.

        Parameters
        ----------
        path : str, optional
            String containing the local/global filepath to the Documentation
            directory. The HTML files will be saved here.
            The default is './Documentation'.
        overwrite : Boolean, optional
            True/False determining whether pre-existing files will be
            overwritten without warning. If False then overwrite will still be
            possible but a warning will appear if there are any pre-existing
            files, which will confirm the user's intention in overwritting or
            otherwise.

        Returns
        -------
        None.
        """
        # we may end up with multiple pages, so initialise Dictionary
        pages = {}
        # filename version of module
        filename = self.module.lower().replace(" ", "_")
        # build top-level page
        pages[filename] = \
            build_page(self.module, self.devs, self.desc, self.classes,
                       self.funcs, self.vars)
        # iterate through classes (if any) and build page for each
        if len(self.classes) > 0:
            for c in self.classes:
                print(f"{filename}.{c}")
                print(c)
                pages[f"{filename}.{c}"] = \
                    build_page(self.module, self.devs,
                    self.classes[c]['description'], classes="",
                    funcs=self.classes[c]['funcs'], submodule=c)

        # finally save all to file
        for page in pages:
            output(pages[page], page, path=path, overwrite=overwrite)
