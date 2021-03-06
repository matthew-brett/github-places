LICENSE
=======

Code license
------------

Copyright 2019 Matthew Brett

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

UN list of countries
--------------------

The file `un_stats_division_countries.csv` contains information about country
codes and classification. It is a very slightly modified copy of a file
downloaded in March 2019 from the [UN statistics
website](https://unstats.un.org/unsd/methodology/m49/overview).  The
modifications are three single-character edits to replace commas in country
names with semi-colons. It's not clear what the license is, but I will assume, until
someone tells me otherwise, that the data are public domain, and can be
distributed freely.

I downloaded `gdp_per_capita.csv` from [The World Bank GDP per capita data inferface](https://data.worldbank.org/indicator/NY.GDP.PCAP.CD).  The World Bank licenses the data under CC-By 4.0; like me, you can redistribute the data freely, as long as you acknowledge its source from the World Bank data site above.

`pop_surface.csv` comes from <http://data.un.org>.  Specifically, it is
a copy of the [population, surface area and
density](http://data.un.org/_Docs/SYB/CSV/SYB61_T02_Population,%20Surface%20Area%20and%20Density.csv)
data table. The [terms of
use](http://data.un.org/Host.aspx?Content=UNdataUse) also allow you to
redistribute the data, but require you to give attribution to its
source, as I have in the links above.

`country_data.csv` is the result of running `process_countries.py` on the CSV files above, to produce a merged data set.  As a derivative, you should cite the UN and the World Bank as data sources.
