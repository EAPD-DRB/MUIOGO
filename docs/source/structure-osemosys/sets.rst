Sets
=================================

The ‘sets’ in OSeMOSYS define the structural elements of the model, which are generally independent of specific scenarios being analyzed. They establish the time domain and its granularity, the spatial coverage, the technologies, and the energy carriers (commodities) included in the system, among other elements. These sets serve as the foundation for indexing variables and parameters.
For example, when a variable is indexed by the set YEAR, it is represented as variablename[y], meaning it is computed for each year listed in the YEAR set. Similarly, other variables and parameters are defined over relevant sets to structure the relationships between technologies, fuels, storage, emissions, and time periods. The sets of OSeMOSYS in MUIO are presented in the below.

REGION [r]
~~~~~~~~~~~~~~
It defines the regions to be modelled, such as different countries. For each region, the supply-demand balance for all commodities is ensured, including trade with other regions. In some cases, it may be computationally more efficient to model multiple countries within the same region and differentiate them using ad hoc commodities and technologies. In MUIO, this set is not available, so the second approach should be used for multi-regional modelling.

TECHNOLOGY [t]
~~~~~~~~~~~~~~
It includes any element of the integrated system that changes a commodity from one form to another, uses it or supplies it. All system components are set up as a ‘technology’ in OSeMOSYS. As the model is an abstraction, the modeller is free to interpret the role of a technology at will, where relevant. It may for example represent a single real technology (such as a power plant) or can represent a heavily aggregated collection of technologies (such as the stock of several million light bulbs) or may even simply be a ‘dummy technology’, perhaps used for accounting purposes.

COMMODITY [f]
~~~~~~~~~~~~~~
It includes any commodity, fuel, service, or proxy that enters or exits technologies. These can be aggregated groups, individual flows, or artificially separated, depending on the analysis requirements. For example, a commodity could be electricity from power plants, land for crop cultivation, or water for public consumption.

EMISSION [e]
~~~~~~~~~~~~~~
It includes any type of emissions that may result from the operation of the defined technologies. Typical examples include atmospheric emissions of greenhouse gases, such as CO₂.

STORAGE [s]
~~~~~~~~~~~~~~
It includes storage facilities in the model, such as dams in a hydropower system or large-scale batteries in the electricity network.

YEAR [y]
~~~~~~~~~~~~~~
It represents the model's time frame and includes all years considered in the study. For example: 2021, 2022, …, 2050.

SEASON [ls]
~~~~~~~~~~~~~~
It provides a sequential numerical indication of the seasons accounted for in the model (e.g., winter, intermediate, summer) and their order. This set is required when storage facilities are included in the model.

DAYTYPE [ld]
~~~~~~~~~~~~~~
It provides a sequential numerical indication of the day types considered in the model (e.g., workday, weekend) and their order. This set is required when storage facilities are included in the model.

DAILYTIMEBRACKET [lh]
~~~~~~~~~~~~~~~~~~~~~
It provides a sequential numerical indication of how the day is divided into parts (e.g., night, morning, afternoon, evening) and their order. This set is required when storage facilities are included in the model.

TIMESLICE [l]
~~~~~~~~~~~~~~
It defines the temporal resolution of the model by splitting each modelled year into representative time slices. This approach, common in several energy system modelling tools (e.g., MESSAGE, MARKAL, TIMES), allows for separate assessment of high- and low-demand periods, particularly for commodities that are costly to store.
While it is possible to create 8,760 time slices to represent each hour of the year, this approach is often computationally intensive. To optimize efficiency, time slices are typically grouped. The annual demand may be divided into aggregate seasons (e.g., summer, winter, intermediate), which can then be further subdivided into day types (e.g., workdays, weekends) and, if necessary, into finer time intervals (e.g., day and night) based on demand variations.

MODE_OF_OPERATION [m]
~~~~~~~~~~~~~~~~~~~~~
This defines the number of operational modes a technology can have. If a technology can use various input or output commodities and choose among different combinations (i.e., any linear combination) of these inputs or outputs, each combination can be considered a separate mode of operation. For example, a combined heat and power (CHP) plant may operate in one mode to produce heat and in another mode to generate electricity.

STORAGEINTRADAY [s]
~~~~~~~~~~~~~~~~~~~
It is a subset of STORAGE that includes storage technologies capable of charging and discharging within a single day (i.e., short-duration storage). This typically includes batteries and other fast-response storage systems.

STORAGEINTRAYEAR [s]
~~~~~~~~~~~~~~~~~~~~
It is subset of STORAGE that includes storage technologies capable of storing energy over long periods, typically across multiple days, weeks, or even seasons. This is also referred to as long-duration or seasonal storage, such as pumped hydro storage and hydrogen storage. 

UDC [u]
~~~~~~~~~~~~~~
The set UDC (User Defined Constraints) allows users to introduce custom constraints beyond the standard OSeMOSYS equations. This adds flexibility to tailor the model for specific policy, technical, or economic constraints that aren't explicitly included in the default formulation. For example, UDCs can represent a reserve margin in a power system or enforce a specific renewable energy target in a sector.

MODEperTECHNOLOGY{TECHNOLOGY} within MODE_OF_OPERATION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It defines the operational modes available for each technology. This means that not every technology will use all possible modes, but only a subset relevant to its function.

MODExTECHNOLOGYperFUELout{COMMODITY} within MODE_OF_OPERATION cross TECHNOLOGY
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It defines which technologies and their modes of operation can produce specific commodities (fuels, electricity, heat, etc.) as outputs. This ensures that not every technology-mode combination produces all fuels, but only a subset relevant to the system.

MODExTECHNOLOGYperFUELin{COMMODITY} within MODE_OF_OPERATION cross TECHNOLOGY
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It defines which technologies and their modes of operation require specific commodities (fuels, electricity, heat, etc.) as inputs. This ensures that only appropriate fuel inputs are assigned to each technology and mode.

MODExTECHNOLOGYperSTORAGEto{STORAGE} within MODE_OF_OPERATION cross TECHNOLOGY
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It defines which technologies and their modes of operation can store/charge energy into specific storage technologies. This ensures that only relevant technologies and modes can charge energy, preventing incorrect assignments.

MODExTECHNOLOGYperSTORAGEfrom{STORAGE} within MODE_OF_OPERATION cross TECHNOLOGY
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It defines which technologies and their modes of operation can extract/discharge energy from specific storage technologies. This ensures that only relevant technologies and modes can discharge energy from storage, preventing incorrect assignments.

MODExTECHNOLOGYperEMISSION{e in EMISSION} within MODE_OF_OPERATION cross TECHNOLOGY
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It defines which technologies (in specific modes of operation) emit specific emissions. This ensures that only technologies that actually produce emissions are assigned them, preventing incorrect emission accounting.

MODExTECHNOLOGYperEMISSIONChange{e in EMISSION} within MODE_OF_OPERATION cross TECHNOLOGY
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It defines which technologies (in specific modes of operation) can reduce or sequester specific emissions. This ensures that only relevant technologies and modes are assigned emission reduction capabilities, preventing incorrect accounting of emission reductions.


