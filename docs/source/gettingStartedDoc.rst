﻿###############
Getting started
###############

**************************
Purpose and Vision of FINE
**************************

FINE is a framework for generating energy system optimization models. This might sound difficult, but the puporse is easy to understand:
FINE is designed to answer pressing questions on future energy systems which include affordability, a high share of renewable energy
sources and - most importantly - low CO\ :sub:`2` emissions.

The concept of FINE is that scientists, programmers and anyone who is interested all around the world can use FINE to answer their
individual questions. Therefore, FINE is open source available and completely for free. Once FINE is installed, you can start
implementing an energy system model that you want to investigate.

************
Installation
************

In the following, instructions for installing and using the FINE framework on Windows are given. The installation
instructions for installing and using FINE on Linux/macOS systems are however quite similar and can be, hopefully
easily, derived from the instructions below.

**Python installation**

FINE runs on Python 3 platforms (i.e. Anaconda). Currently, it is advised not to use a Python version exceeding
Python 3.6. Note: When installing the Python platform Anaconda the options

    $ Add Anaconda to the system PATH environment variable

is available in the advanced installation option. When selecting this options, the environment variables for Python,
pip, jupyter etc. are remotely set and do not have to be manually set.

A development platform which can be used to work with/on the code and which comes with Anaconda is Spyder.
Other development platforms are PyCharm or Visua Studio Code.

**FINE installation**

Install via pip by typing

    $ pip install FINE

into the command prompt. Alternatively, download or clone a local copy of the repository to your computer

    $ git clone https://github.com/FZJ-IEK3-VSA/FINE.git

and install FINE in the folder where the setup.py is located with

    $ pip install -e .

or install directly via python as

    $ python setup.py install

**Installation of additional packages**

The Python packages `tsam <https://github.com/FZJ-IEK3-VSA/tsam>`_ and `PYOMO <http://www.pyomo.org/>`_ should be
installed by pip alongside FINE. Some plots in FINE require the GeoPandas package to be installed (nice-to-have).
Installation instructions are given `here <http://geopandas.org/install.html>`_. In some cases, the dependencies of
the GeoPandas package have to be installed manually before the package itself can be installed.

**Installation of an optimization solver**

In theory many solvers can be used (e.g. `GUROBI <http://www.gurobi.com/>`_  or
`GLPK <https://sourceforge.net/projects/winglpk/files/latest/download>`_). For the installation of GUROBI, follow
the instructions on the solver's website. GUROBI has, if applicable, an academic license option. For installation
of GLPK, move the downloaded folder to a desired location. Then, manually append the Environment Variable *Path*
with the absolute path leading to the folder in which the glpsol.exe is located (c.f. w32/w64 folder, depending on
operating system type).

********
About Us
********

.. image:: https://www.fz-juelich.de/iek/iek-3/DE/_Documents/Pictures/IEK-3Team_2019-02-04.jpg?__blob=poster
    :target: https://www.fz-juelich.de/iek/iek-3/EN/Home/home_node.html
    :alt: Abteilung TSA
    :align: center

We are the `Institute of Energy and Climate Research - Techno-economic Systems Analysis (IEK-3) <https://www.fz-juelich.de/iek/iek-3/DE/Home/home_node.html>`_ 
belonging to the `Forschungszentrum Jülich <www.fz-juelich.de/>`_. Our interdisciplinary institute's research is 
focusing on energy-related process and systems analyses. Data searches and system simulations are used to 
determine energy and mass balances, as well as to evaluate performance, emissions and costs of energy systems. 
The results are used for performing comparative assessment studies between the various systems. Our current priorities 
include the development of energy strategies, in accordance with the German Federal Government’s greenhouse gas reduction 
targets, by designing new infrastructures for sustainable and secure energy supply chains and by conducting cost analysis 
studies for integrating new technologies into future energy market frameworks.


**Contributions and Users**

Within the BMWi funded project `METIS <http://www.metis-platform.net/>` we develop together with the RWTH-Aachen 
`(Prof. Aaron Praktiknjo) <http://www.wiwi.rwth-aachen.de/cms/Wirtschaftswissenschaften/Die-Fakultaet/Institute-und-Lehrstuehle/Professoren/~jgfr/Praktiknjo-Aaron/?allou=1&lidx=1>`_,
the EDOM Team at FAU `(PD Bismark Singh) <https://www.math.fau.de/wirtschaftsmathematik/team/bismark-singh/>`_ and the 
`Jülich Supercomputing Centre (JSC) <http://www.fz-juelich.de/ias/jsc/DE/Home/home_node.html>`_ new methods and models within FINE.

.. image:: http://www.metis-platform.net/metis-platform/DE/_Documents/Pictures/projectTeamAtKickOffMeeting_640x338.jpg?__blob=normal
    :target: http://www.metis-platform.net
    :alt: METIS Team
    :align: center

Dr. Martin Robinius is teaching a `course <https://www.campus-elgouna.tu-berlin.de/energy/v_menu/msc_business_engineering_energy/modules_and_curricula/project_market_coupling/>`_
at TU Berlin in which he is introducing FINE to students.