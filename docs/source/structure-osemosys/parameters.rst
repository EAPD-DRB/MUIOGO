###########################
Parameters
###########################

Parameters are user-defined numerical inputs to the model. While the model structure defined by the sets typically remains fixed across scenarios, it is common practice to adjust parameter values for scenario analysis or sensitivity studies. Each parameter is associated with one or more sets. For instance, **CapitalCost[r,t,y]** indicates that capital cost varies by region (r), technology (t), and year (y). The information below provides a list and brief description of the parameters included in the version of OSeMOSYS in MUIO.

Global Parameters
-----------------

Discount rate [Region]
++++++++++++++++++++++

In present value analysis, the discount rate [Region] represents the time preference rate used to “discount” future cash flows into their present value. The concept of time value of money recognizes that a dollar received in the future is worth less than a dollar received today due to factors such as opportunity cost and risk. Therefore, to compare costs and benefits occurring at different points in time, they need to be adjusted to their present value. The discount rate parameter sets this rate of time preference and is used to determine the equivalent value in today’s money of future costs and benefits.
A higher discount rate indicates a higher opportunity cost or a higher required return, which means that future cash flows are worth less in present value terms. Conversely, a lower discount rate means that future cash flows are worth more in present value.
The discount rate is expressed as a fraction (i.e. it will have a value between 0 and 1) and reflects the relevant time preference or opportunity cost of capital.

Discount rate ldv [Region, Technology]
++++++++++++++++++++++++++++++++++++++

The Discount rate ldv [Region, Technology] parameter can be used to specify a technology specific discount rate. It can be set when the user wants a discount rate that is different from the general time preference rate (specified with the Discount rate parameter) to be applied to a technology. For technologies with a technology specific discount rate, the investment will be annualized based on the rate set by the Discount rate ldv parameter and the present value of the resulting series of annual payments will be calculated based on the general time preference rate (Discount rate parameter).
This parameter can for instance be used to adjust for differences in the perceived risk of investment in a technology. For instance, a lower discount rate might be applied for renewable power generation technologies that sell electricity on power purchasing agreements or have access to concessional finance sources, than fossil fuel technologies selling electricity in open markets and are subject to environmental regulation risks.
The Discount rate Idv is expressed as a fraction (i.e. it will have a value between 0 and 1).

Year Split [Region, Year, Timeslice]
++++++++++++++++++++++++++++++++++++
The Year Split [Region, Year, Time-slice] parameter is used to set the duration of each time slice (sub-annual time increment of the model). It is a time-dependent parameter and is specified as a fraction of the total year for each time-slice in each year (i.e. it will have a value between 0 and 1).
For example, if a time-slice represents peak demand (demand during the hour of the day when demand is highest) in one season of the year (e.g. summer) and that season lasts 3 months (i.e. a quarter of the year), then the Year Split for that time slice would be 0.25 (duration of the season as a share of the full year – i.e. 3 months out of 12 months) times 1/24 (proportional duration of the peak hour over as a share of a day – i.e. 1 hour out of 24 hours) , which equals 0.0104.
The summation of the Year Split over one year should be equal to 1 (except for small rounding errors).

Capital Recovery Factor [Region, Technology]
++++++++++++++++++++++++++++++++++++++++++++

The Capital Recovery Factor [Region, Technology] parameter is used to convert a lump-sum capital investment into an equivalent annualized cost over the operational lifetime of a technology. It ensures that capital costs are appropriately distributed over the years during which the asset is used, aligning them with the model’s annual accounting framework. It is calculated in a post-processing step in MUIO.

PV Annuity [Region, Technology]
+++++++++++++++++++++++++++++++

The PV Annuity [Region, Technology] parameter is used to discount recurring annual costs (like Operation & Maintenance) over a technology’s lifetime, bringing them to a present value equivalent at the time of investment. It is calculated in a post-processing step in MUIO.

Demand Parameters
-----------------

Accumulated Annual Demand [Region, Year, Commodity]
+++++++++++++++++++++++++++++++++++++++++++++++++++

OSeMOSYS models are “demand driven” meaning that the objective is to meet user specified demands at the lowest possible cost. Needs for investment and operation of facilities designed to produce a specific commodity are driven by the level of demand for that commodity.
The Accumulated Annual Demand [Region, Year, Commodity] parameter is one of two alternative parameters used to specify such demands (the other being Specified Annual Demand). It is typically used for commodity demands where the exact timing of the supply and demand are not important (e.g. if the commodity is easy to store). This can for instance be used to specify demand for grains. Grains are typically harvested at certain times of the year but consumed throughout the year. The fact that the production and consumption happen at different times of the year does not matter because storage in silos, warehouses or pantries is readily available and cheap.
Accumulated Annual Demand is specified per commodity and can vary from year to year, It sets the level of demand and is specified in the units of the commodity in question. It typically increases over time with rising population and incomes. When the Accumulated Annual Demand is set for a certain commodity, a Specified Annual Demand should not be set for that same commodity.

Specified Annual Demand [Region, Year, Commodity]
+++++++++++++++++++++++++++++++++++++++++++++++++

The Specified Annual Demand [Region, Year, Commodity] parameters is one of two alternative parameters used to specify such demands (the other being Accumulated Annual Demand). It is typically used for commodity demands where the exact timing of the supply and demand is important. This would in particular apply to electricity where supply and demands need to be balanced in real time to ensure reliability and quality of power supply.
Specified Annual Demand is set per commodity and can vary from year to year. It sets the level of demand and is specified in the units of the commodity in question. It typically increases over time with rising population and incomes. It needs to be paired with the Specified Demand Profile parameter which is used to allocate the demand to each time slice.
When the Specified Annual Demand is set for a certain commodity, an Accumulated Annual Demand should not be set for that same commodity.

Specified Demand Profile [Region, Year, Commodity, Timeslice]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Specified Demand Profile [Region, Year, Commodity, Time slice] parameter is used to describe the variation in Specified Annual Demand across different times of the year. More specifically, it sets the share of demand that occurs in each time slice, specified as a fraction of the total demand in that year (a number between 0 and 1). The summation of the Specified Demand Profile over one year should be equal to 1 (except for small rounding errors).
The Specified Demand Profile is set per commodity and can vary from year to year. It needs to be paired with the Specified Annual Demand which is used to set the total demand level.

Performance Parameters
----------------------

Availability Factor [Region, Year, Technology]
++++++++++++++++++++++++++++++++++++++++++++++

The Availability Factor [Region, Year, Technology] parameter is typically used to model the operational constraints or limitations of a particular technology (e.g. to account for time a technology needs to be offline for maintenance or for overall energy availability constraints). It represents the average available capacity as a fraction of the total design capacity.
For example, if a gas-fired power plant has planned maintenance scheduled for 500 hours in a year (approximately 6% of the total year), then the average available capacity is 94% of the total. This is represented by an availability factor of 0.94.
Similarly, if a hydroelectric power plant only has water inflow to produce 60% of the theoretical maximum output of the plant, this can be represented as an availability factor of 0.6.
The Availability Factor is specified for each technology in each year.

Capacity Factor [Region, Year, Technology, Timeslice]
+++++++++++++++++++++++++++++++++++++++++++++++++++++

The Capacity Factor [Region, Year, Technology, Time slice] parameter is typically used to model seasonal operational constraints or limitations of a particular technology (e.g. to account for time a technology needs to be offline for maintenance or for overall energy availability constraints). It represents the average available capacity as a fraction of the total design capacity for each time slice. It is similar to the Availability Factor parameter but is applied when there are factors outside the control of the operator that impact the technology availability across seasons or time of day.
For example, consider representation of a solar photovoltaic panel in a simple model with one time-slice representing daytime and another time slice representing nighttime. It will generate power during the day power when the sun shines (let us say 50% of design capacity on an average day), but not during the night (battery storage can be represented separately). The Capacity Factor should in this case be set to 0.5 (50%) during the day time-slice and 0 for the night time slice.
The Capacity Factor is specified for each technology, in each time slice in each year. Note that the default value is set to 1, which would mean no seasonal dependencies. For any technology that has no externally induced differences in availability over the course of a year, the default value can therefore be left as is and no data entry is needed.

Capacity To Activity Unit [Region, Technology]
++++++++++++++++++++++++++++++++++++++++++++++

The CapacityToActivityUnit [Region, Technology] parameter is used to define the relationship between the capacity of a technology and the activity unit associated with it. It represents the maximum amount of activity that can be performed by a technology if one unit of capacity works at full load for a full year.
For example, if the capacity of a power plant is measured in megawatts (MW) and the activity is measured in terajoules (TJ), the CapacityToActivityUnit parameter will specify how many terajoules one megawatt of capacity can generate in one year (i.e. TJ/MW).
CapacityToActivityUnit is time-independent and defined for each technology. It is specified in the applicable ratio of units of activity and capacity for that technology.

Input Activity Ratio [Region, Year, Technology, Commodity, Mode of Operation]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The InputActivityRatio [Region, Year, Technology, Commodity, Mode of Operation] parameter is used to specify how much of an input is needed to support the Activity of a Technology. It specifies how many units of input are needed for each unit of activity.
As an example, consider a natural gas fired power station with a conversion efficiency is 50%. The input to the plant is natural gas and the Activity represents electricity generated. This means that for every unit of electricity generated, 2 units (1/50%) of natural gas are needed. Consequently, the InputActivityRatio should be set to 2 in this case.
The unit of this parameter depends on the units chosen for the input commodity and for the Activity units chosen for the technology.
The InputActivityRatio is specified for each technology/commodity combination. If a technology has 2 or more inputs, then one InputActivityRatio is needed for each pairing. The parameter is time dependent and can vary from year to year.

Input To New Capacity Ratio [Region, Year, Technology, Commodity]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The InputToNewCapacityRatio [Region, Year, Technology, Commodity] parameter is used to specify how much of an input is needed to support investment in a Technology. It specifies how many units of input are needed for each unit of new capacity added. This parameter can for instance be used to represent the amount of materials used in the construction of new facilities.
As an example, consider a scenario where a new 2MW wind turbine would require 300 tonnes of steel. The InputToNewCapacityRatio would be the number of tonnes of steel required for each MW of capacity (300 tonnes/2MW = 150 tonnes/MW).
The InputToNewCapacityRatio is specified for each technology/commodity combination. The parameter is time dependent and can vary from year to year.

Input To Total Capacity Ratio [Region, Year, Technology, Commodity]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The InputToTotalCapacityRatio [Region, Year, Technology, Commodity] parameter is used to specify how much of an input is needed for ongoing support to maintaining capacity of a Technology. It specifies how many units of input are needed for each unit of total capacity installed.
This parameter can for instance be used to represent the amount of land a technology occupies. As an example, consider a 50 MW solar PV installation that covers 1.5 square kms. The ratio of input (land) to capacity is 1.5/50=0.03, which means that the InputToTotalCapacityRatio parameter should be set to 0.03 square kms per MW.
The InputToTotalCapacityRatio is specified for each technology/commodity combination. The parameter is time dependent and can vary from year to year.

Output Activity Ratio [Region, Year, Technology, Commodity, Mode of Operation]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The OutputActivityRatio [Region, Year, Technology, Commodity, Mode of Operation] parameter is used to specify how much output is generated from the Activity of a Technology. It specifies how many units of output are produced for each unit of activity.
As an example, consider maize cultivation. The Activity of the maize cultivation could represent how much land is planted with maize (measured in hectares), while the output would be the number of tonnes of maize produced. If 1,000 hectares of maize cultivation yield 4,500 tonnes, then the ratio of output to activity is 4.5 (4,500/1,000). Consequently, the OutputActivityRatio should be set to 4.5 tonnes per hectare in this case.
The unit of this parameter depends on the units chosen for the output commodity and the activity units set for the technology.
The OutputActivityRatio is specified for each technology/commodity combination. If a technology has 2 or more outputs, then one OutputActivityRatio is needed for each pairing. The parameter is time dependent and can vary from year to year.

Operational Life [Region, Technology]
+++++++++++++++++++++++++++++++++++++

The OperationalLife [Region, Technology] parameter is used to define the lifespan of a technology or system. It represents the number of years a technology or system can be operational before it is decommissioned or needs to be replaced.
The OperationalLife [Region, Technology] parameter is time-independent and defined for each technology. It is specified in number of years.

Residual Capacity [Region, Year, Technology]
++++++++++++++++++++++++++++++++++++++++++++

The Residual Capacity [Region, Year, Technology] parameter represents capacity installed prior to the model period and can be used to specify any existing capital stock available in the base year if the analysis.
Residual Capacity is specified in units of capacity for each technology and should be entered for each year the capital stock is expected to remain available. If capacity is expected to be retired during the model horizon the value provided for this parameter should be reduced accordingly.

Costing Parameters
------------------

Capital Cost [Region, Year, Technology]
+++++++++++++++++++++++++++++++++++++++

The Capital Cost [Region, Year, Technology] parameter is used to specify the investment cost associated with the construction or installation of a technology. It represents the initial investment required to acquire, construct or expand new technology capacity.
Capital Cost is defined for each technology or infrastructure component in the OSeMOSYS model and represents the cost per unit of capacity. It includes expenses such as equipment, construction, engineering, installation, land acquisition, and any other costs associated with the capital investment.

Fixed Cost [Region, Year, Technology]
+++++++++++++++++++++++++++++++++++++

The Fixed Cost [Region, Year, Technology] parameter is used to specify any costs incurred to keep technology available and operational. It can include items such as salaries, rent, property taxes and insurance amongst others. All operational costs that are independent of the level of Activity (utilization) of the technology should be included. Any costs that vary with the level of Activity such as inputs and other consumables should be specified under the Variable Cost parameter.
Fixed Costs are specified on a per unit of capacity basis (e.g. $/kW) and can change from year to year.

Variable Cost [Region, Year, Technology, Mode of Operation]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Variable Cost [Region, Year, Technology, Mode of Operation] parameter is used to specify any costs incurred to operate a technology. It can include items such as inputs and other consumables amongst others. All operational costs that are dependent on the level of Activity (utilization) of the technology should be included. Any operational costs that are independent of the level of Activity such as salaries, rent, property taxes and insurance etc. should be specified under the Fixed Cost parameter.
Variable Costs are specified on a per unit of activity basis (e.g. $/GJ) and can change from year to year or between different modes of operation.

Emissions penalty [Region, Emission, Year]
++++++++++++++++++++++++++++++++++++++++++

The emissions penalty [Region, Emission, Year] parameter is used to assign a cost to the release of an emission. It can represent an actual charge such as a tax or penalty, or an external cost that is not formally monetized. A negative value can be used to represent a credit or subsidy.
The AnnualEmissionLimit parameter is defined for each emission and can be changed from year to year. It is specified in currency units per unit of emission (e.g. $/tonne).

Storage Parameters
------------------

Operational Life Storage [Region, Storage]
++++++++++++++++++++++++++++++++++++++++++

The Operational Life Storage [Region, Storage] parameter is used to define the lifespan of a storage asset. It represents the number of years a storage can be operational before it is decommissioned or needs to be replaced. The OperationalLife parameter is time-independent and defined for each storage. It is specified in number of years.

Capital Cost Storage [Region, Storage, Year]
++++++++++++++++++++++++++++++++++++++++++++

The Capital Cost Storage [Region, Year, Storage] parameter is used to specify the investment cost associated with the construction or installation of a storage facility. It represents the initial investment required to acquire, construct or expand storage capacity. Capital Cost Storage is defined for each storage and represents the cost per unit of storage capacity. It includes expenses such as equipment, construction, engineering, installation, land acquisition, and any other costs associated with the capital investment.

Residual Storage Capacity [Region, Storage, Year]
+++++++++++++++++++++++++++++++++++++++++++++++++

The Residual Capacity [Region, Year, Storage] parameter represents storage capacity installed prior to the model period and can be used to specify any existing capital stock available in the base year of the analysis. Residual Capacity is specified in units of capacity for each storage and should be entered for each year the capital stock is expected to remain available. If capacity is expected to be retired during the model horizon the value provided for this parameter should be reduced accordingly.

Technology To Storage [Region, Technology, Storage, Mode of Operation]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Technology To Storage [Region, Technology, Storage, Mode of Operation] parameter is a tag to identify technologies that provide input to storage. It is set to 1 when the link exists and to 0 when there is no link. For example, a utility scale battery may use electricity provided by the transmission grid as input. In this case a value of 1 should be provided for the combination of the transmission grid technology and the battery storage. Technology To Storage is dimensionless and can be provided for each region, technology, storage and mode of operation. It should be set to either 0 (no link) or 1 (link exists).

Technology from Storage [Region, Technology, Storage, Mode of Operation]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Technology from Storage [Region, Technology, Storage, Mode of Operation] parameter is a tag to identify technologies that receive the output from a storage. It is set to 1 when the link exists and to 0 when there is no link. For example, a utility scale battery may provide electricity for distribution to final users. In this case a value of 1 should be provided for the combination of the distribution grid technology and the battery storage. Technology from Storage is dimensionless and can be provided for each region, technology, storage and mode of operation. It should be set to either 0 (no link) or 1 (link exists).

Storage Level Start [Region, Storage]
+++++++++++++++++++++++++++++++++++++

The Storage Level Start [Region, Storage] is used to specify the storage level at the start of the first period. The parameter value is expressed in relation to the maximum capacity of the storage system and given as a fraction (e.g. 0.5 to indicate a storage that is half-full at the start of the model period).

Min storage charge [Region, Year, Storage]
++++++++++++++++++++++++++++++++++++++++++

The Min storage charge [Region, Year, Storage] parameter is used to specify a lower limit on the amount of storage at any given time. This can for instance be used to represent a storage dam, where a certain minimum water level should be maintained at all times or to restrict the operation of a battery to ensure that it is never fully depleted. The parameter value is expressed in relation to the maximum capacity of the storage system and given as a fraction (e.g. 0.2 to indicate a that the storage level should not drop below 20% of maximum capacity). It is provided for each year for each storage asset in the model.

Conversion ls [Timeslice, Season]
+++++++++++++++++++++++++++++++++

Binary parameter linking one TimeSlice to a certain Season. It has value 0 if the TimeSlice does not pertain to the specific season, 1 if it does.

Conversion ld [Timeslice, DayType]
++++++++++++++++++++++++++++++++++

Binary parameter linking one TimeSlice to a certain DayType. It has value 0 if the TimeSlice does not pertain to the specific DayType, 1 if it does.

Conversion lh [Timeslice, DailyTimeBracket]
+++++++++++++++++++++++++++++++++++++++++++

Binary parameter linking one TimeSlice to a certain DaylyTimeBracket. It has value 0 if the TimeSlice does not pertain to the specific DaylyTimeBracket, 1 if it does.

Day Split [Region, Year, Timeslice]
+++++++++++++++++++++++++++++++++++

The Day Split [Region, Year, Timeslice] parameter is used to set the duration of an individual occurrence of each time slice (sub-annual time increment of the model). It is a time-dependent parameter and is specified as a fraction of the total year for each time-slice in each year (i.e. it will have a value between 0 and 1). The parameter is only used in the representation of storage.
For example, if a time-slice represents peak demand (demand during the hour of the day when demand is highest) then the parameter should be set to 1/8760 = 0.000114 (8760 is the number of hours in a year), while if it represents the base load period (e.g. 9pm to 6am = 9 hours) then it should be set to 9/8760 = 0.001027. The DaySplit parameter is provided for each timeslice and can change from year to year.

Days In Day Type [Region, Year, Season, Daytype]
++++++++++++++++++++++++++++++++++++++++++++++++

The Days In Day Type [Region, Year, Season, Daytype] is used to specify the number of sequential days in a single occurrence of a day type. For example, if a day type represents weekdays the parameter value should be set to 5, while for a day type representing a weekend it should be set to 2. It is specified for each daytype in each season. It can change from year to year although this would only be applicable in special circumstances when the user wishes to change the time representation at a point within the model horizon.

Capacity Parameters
-------------------

Capacity Of One Technology Unit [Region, Year, Technology]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Capacity Of One Technology Unit [Region, Year, Technology] parameter can be used to ensure that capacity additions only occur in discrete increments. This is typically used for large facilities of a specific design where there is little or no flexibility to scale the size of the investment to needs.
For example, a technology can be used to represent a specific hydropower site and design, which should either be built in full or not at all. This is in contrast to a wind farm for instance, which can be scaled to virtually any size. If the user wants to represent a 500MW hydropower plant, a value of 500 could be provided for the Capacity Of One Technology Unit, to ensure that only investment of 500MW at a time is possible. Investment in multiples of 500MW (e.g. 1,000 MW, 1,500 MW etc.) would still be possible, so if the user wants to avoid this, the Total Annual Max capacity parameter can be used to limit total investment.
Note that use of this parameter can impact solution times considerably as the optimization problem is no longer linear.

Total Annual Max capacity [Region, Year, Technology]
++++++++++++++++++++++++++++++++++++++++++++++++++++

Total Annual Max capacity [Region, Year, Technology] parameter is specified when there is an upper restriction on the overall capacity of a particular technology. It establishes a maximum limit on the total capacity within a year. This could for instance be used to ensure that a hydro powerplant representing a specific site does not exceed the estimated potential for that site.
Total Annual Max capacity is specified in units of capacity of the relevant technology and can change from year to year.

Total Annual Max capacity investment [Region, Year, Technology]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Total Annual Max capacity investment [Region, Year, Technology] parameter is specified when there is a limitation on how quickly the capacity of a specific technology can be expanded. It sets a direct upper bound on new capacity installations in a year. This could for instance be used restrict investment in rooftop solar to what the domestic industry is currently capable of installing (e.g. due to limitations on skilled labor to install panels)
Total Annual Max capacity investment is specified in units of capacity of the relevant technology and can change from year to year.

Annual min capacity [Region, Year, Technology]
++++++++++++++++++++++++++++++++++++++++++++++

Annual min capacity [Region, Year, Technology] parameter is specified when there is a minimum requirement for the overall capacity of a particular technology. It establishes a lower limit on the total capacity within a year. This could for instance be used to enforce a regulatory requirement (e.g. impose a certain target for total installed wind capacity in a given year).
Annual min capacity is specified in units of capacity of the relevant technology and can change from year to year.

Annual min capacity investment [Region, Year, Technology]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Annual min capacity investment [Region, Year, Technology] parameter is specified when there is a minimum requirement for investment in a technology in a given year. It sets a lower bound on total capacity installations in a year. This could for instance be used to ensure the construction of a plant for which the commitment to invest has already been made (e.g. a facility that is already under construction but not expected to be operational until a future year).
Annual min capacity investment is specified in units of capacity of the relevant technology and can change from year to year.

Activity Parameters
-------------------

Technology Annual Activity by Mode Lower Limit [Region, Year, Technology, Mode of Operation]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Technology Annual Activity by Mode Lower Limit [Region, Year, Technology, Mode of Operation] parameter is specified when there is a clear lower restriction on the overall operation of a particular technology. It establishes a lower limit on the total activity of a technology within a year for each mode of operation. This could for instance be used to ensure that the operation of any “must-run” facilities is within requirements, or if there are legal mandates requiring a certain minimum output (e.g. a goal of producing a certain level of biofuels in a given year).
Technology Annual Activity by Mode Lower Limit is specified in units of activity of the relevant technology and can change from year to year.

Technology Annual Activity by Mode Upper Limit [Region, Year, Technology, Mode of Operation]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Technology Annual Activity by Mode Upper Limit [Region, Year, Technology, Mode of Operation] parameter is specified when there is a clear maximum restriction on the overall operation of a particular technology. It establishes an upper limit on the total activity of a technology within a year for each mode of operation. This could for instance be used to ensure that certain renewable flow (e.g. fresh water) stay below sustainable extraction levels or that mandated maximum allowable output restrictions are observed.
Technology Annual Activity by mode Upper Limit is specified in units of activity of the relevant technology and can change from year to year.

Technology Activity Decrease By Mode Limit [Region, Year, Technology, Mode of Operation]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Technology Activity Decrease By Mode Limit [Region, Year, Technology, Mode of Operation] parameter is used to ensure that the activity of a technology does not decrease by more than a certain share each year. For example, a parameter value of 0.05 would indicate that activity could only drop by 5% from one year to the next. This can be used to represent market friction, when it is thought that market actors will not be quick to abandon a technology.
Technology Activity Decrease By Mode Limit is time dependent and can change from year to year.

Technology Activity Increase By Mode Limit [Region, Year, Technology, Mode of Operation]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Technology Activity Increase By Mode Limit [Region, Year, Technology, Mode of Operation] parameter is used to ensure that the activity of a technology does not increase by more than a certain share each year. For example, a parameter value of 0.1 would indicate that activity could only increase by 10% from one year to the next. This can be used to represent market friction, when it is thought that the rate of market adoption will be limited to a certain growth rate.
Technology Activity Increase By Mode Limit is time dependent and can change from year to year.

Total Technology Annual Activity Lower Limit [Region, Year, Technology]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Total Technology Annual Activity Lower Limit [Region, Year, Technology] parameter is specified when there is a clear lower restriction on the overall operation of a particular technology. It establishes a lower limit on the total activity (from all modes of operation) within a year. This could for instance be used to ensure that the operation of any “must-run” facilities is within requirements, or if there are legal mandates requiring a certain minimum output (e.g. a goal of producing a certain level of biofuels in a given year).
Total Technology Annual Activity Lower Limit is specified in units of activity of the relevant technology and can change from year to year.

Total Technology Annual Activity Upper Limit [Region, Year, Technology]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Total Technology Annual Activity Upper Limit [Region, Year, Technology] parameter is specified when there is a clear maximum restriction on the overall operation of a particular technology. It establishes an upper limit on the total activity (from all modes of operation) within a year. This could for instance be used to ensure that certain renewable flows (e.g. fresh water) stay below sustainable extraction levels or that mandated maximum allowable output restrictions are observed.
Total Technology Annual Activity Upper Limit is specified in units of activity of the relevant technology and can change from year to year.

Total Technology Model Period Activity Lower Limit [Region, Technology]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Total Technology Model Period Activity Lower Limit [Region, Technology] parameter is used to impose a minimum level of cumulative activity for a technology over the entire model horizon (i.e. all model years) and all modes of operation. The sum of activity for the technology over all model years must be greater than the specified amount.
The Total Technology Model Period Activity Lower Limit parameter is time-independent and defined for each technology. It is specified in the applicable units of activity for that technology.

Total Technology Model Period Activity Upper Limit [Region, Technology]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Total Technology Model Period Activity Upper Limit [Region, Technology] parameter is used to impose a maximum level of cumulative activity for a technology over the entire model horizon (i.e. all model years) and all modes of operation. The sum of activity for the technology over all model years must be less than the specified amount.
This parameter can for instance be used to represent the total extent of an exhaustible resource, such as an oil reservoir or a coal deposit. In this case the parameter value should be set equal to the estimated recoverable reserve of the resource, beyond which further extraction would not be possible.
The Total Technology Model Period Activity Upper Limit parameter is time-independent and defined for each technology. It is specified in the applicable units of activity for that technology.

UDC Parameters
-----------------
User-defined Constraints (UDCs) can be used to specify relationships between model variables. They can be created as either equalities or inequalities and consist of a constant (representing the right-hand side of the equation or inequality) and a set of multipliers for different variables (Capacity, New Capacity and Activity representing the left-hand side).
.. math::

   \sum_{t} \left( 
       \text{UDC\_Multiplier\_New\_Capacity}_t \cdot \text{New\_Capacity}_t +
       \text{UDC\_Multiplier\_Total\_Capacity}_t \cdot \text{Total\_Capacity}_t +
       \text{UDC\_Multiplier\_Activity}_t \cdot \text{Activity}_t
   \right) \leq \text{UDC\_Constant}

UDC Multiplier Activity [Region, Year, Technology, Constraint]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The UDC Multiplier Activity sets a technology specific value that will be multiplied with Activity for each technology on the left-hand side of the equality/inequality as shown in the equation below, where t represents the technology and n is the total number of technologies.
For example, if the user wishes to set a target of 40% renewable power generation as a share of total power generation, the UDC constant can be set to 0, a value of 0.4 can be specified for the UDC Multiplier Activity for all non-renewable power generation technologies and a value of -0.6 (1-0.4) can be specified for all renewable technologies. This means that the left-hand side of the equation should equal the target value (40%) times total generation minus total renewable generation, which will need to be less than the UDC constant value (zero) so that renewable generation is always higher than 40% of total generation. Note the transposition (the negative 0.4) that has taken place because renewable generation is also part of total generation.
The UDC multipliers are constraint, year and technology specific, so that a technology that is included in more than one constraint can have different multiplier values for each constraint, technologies in the same constraint can have different multiplier values and that the multiplier values can vary from year to year.

UDC Multiplier New Capacity [Region, Year, Technology, Constraint]
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The UDC Multiplier New Capacity sets a technology specific value that will be multiplied with New Capacity for each technology on the left-hand side of the equality/inequality as shown in the equation below, where t represents the technology and n is the total number of technologies.
For example, if the user wishes to restrict the total investment in total wind power capacity to 500MW per year, the UDC constant can be set to 500 and a value of 1 can be specified for the UDC Multiplier New Capacity for all wind power technologies (and zero for everything else). This means that the left-hand side of the equation should equal total new capacity and will be restricted by the inequality to always remain below or equal to the UDC constant value.
The UDC multipliers are constraint, year and technology specific, so that a technology that is included in more than one constraint can have different multiplier values for each constraint, technologies in the same constraint can have different multiplier values and that the multiplier values can vary from year to year.

UDC Total Capacity [Region, Year, Technology, Constraint]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The UDC Multiplier Total Capacity sets a technology specific value that will be multiplied with Total Capacity for each technology on the left-hand side of the equality/inequality as shown in the equation below, where t represents the technology and n is the total number of technologies.
For example, if the user wishes to restrict the total hydropower capacity to 2000MW per year, the UDC constant can be set to 2000 and a value of 1 can be specified for the UDC Multiplier Total Capacity for all hydro power technologies (and zero for everything else). This means that the left-hand side of the equation should equal total capacity of hydro power technologies and will be restricted by the inequality to always remain below or equal to the UDC constant value.
The UDC multipliers are constraint, year and technology specific, so that a technology that is included in more than one constraint can have different multiplier values for each constraint, technologies in the same constraint can have different multiplier values and that the multiplier values can vary from year to year.

UDC Constant [Region, Year, Constraint]
+++++++++++++++++++++++++++++++++++++++

The UDC Constant sets the right-hand side value of inequality or equality as per the equation below, where t represents the technology and n is the total number of technologies.
For example, if the user wishes to restrict the total investment in total wind power capacity to 500MW per year, the UDC constant can be set to 500 and a value of 1 can be specified for the UDC Multiplier New Capacity for all wind power technologies (and zero for everything else). This means that the left-hand side of the equation should equal total new capacity and will be restricted by the inequality to always remain below or equal to the UDC constant value.
The UDC multipliers are constraint, year and technology specific, so that a technology that is included in more than one constraint can have different multiplier values for each constraint, technologies in the same constraint can have different multiplier values and that the multiplier values can vary from year to year.

UDC Tag [Region, Constraint]
++++++++++++++++++++++++++++

This parameter specifies whether the constraint is defined as an equality or an inequality.

Emission Parameters
-------------------

Emission Activity Ratio [Region, Year, Technology, Emission, Mode of operation]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Emission Activity Ratio [Region, Year, Technology, Emission, Mode of operation] is used to set an emission factor for a technology. It defines the relationship between the activity of a technology and its emissions, by indicating how many emission units are released for every unit of activity.
For example, the combustion of 1 GJ of natural gas will release 50.2 tonnes of CO2 into the atmosphere. If a natural gas fired power plant has an efficiency of 50% then 2 GJ of natural gas is needed to generate 1 GJ of electricity. The Emission Activity Ratio is the ratio of emissions (2*50.2=100.4 tonnes CO2) to activity (1 GJ of generated electricity) and should be set to 100.4 (t CO2/GJ).
Emission Activity Ratio is technology and emission specific and can change from year to year and between modes of operation.

AnnualEmissionLimit [Region, Emission, Year]
++++++++++++++++++++++++++++++++++++++++++++

The AnnualEmissionLimit [Region, Emission, Year] parameter is used to set an upper limit on emissions in a particular year. It will set a total maximum allowable cap on emissions that cannot be exceeded.
This parameter can for instance be used to model carbon mitigation scenarios. GHG mitigation goals are often specified as a target in a specific year (e.g. 30% reductions by 2030) and this parameter can be used to represent this.
The AnnualEmissionLimit parameter is defined for each emission and can be changed from year to year. It is specified in the applicable units of that emission.

Model Period Emission Limit [Region, Emission]
++++++++++++++++++++++++++++++++++++++++++++++

The parameter Model Period Emission Limit [Region, Emission] parameter is used to set a cumulative limit on emissions over the entire model horizon (i.e. all years).
The parameter can for instance be used to model carbon mitigation scenarios and carbon budgets. Since climate change impacts are ultimately determined by total cumulative greenhouse gas emission (GHG), reducing total emissions over time is more important than reaching an emission target for a given year. This parameter therefore lets users directly limit GHG impacts on climate, while allowing for the emission reduction pathway to be optimized.
The ModelPeriodEmissionLimit parameter is time-independent and defined for each emission. It is specified in the applicable units of that emission.

Emission To Activity Change Ratio [Region, Year, Technology, Emission, Mode of Operation]
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The Emission To Activity Change Ratio [Region, year, technology, emission, mode of operation] is an emission factor applied to the change in Activity of a technology from one year to the next. It specifies how many units of emission are released for every unit of change in activity compared to the previous year.
This parameter can for instance be used to model land-use change emission. A decrease in forested area for example, would be evident in the reduction in activity (land coverage) of the technology representing forests. By providing this ratio (i.e. the carbon stored per unit of forested area) the emissions associated with the loss of forests can be calculated. Since land is a carbon sink, the emission Emission To Activity Change Ratio will usually be negative.
Emission To Activity Change Ratio is technology and emission specific and can change from year to year and between modes of operation.
