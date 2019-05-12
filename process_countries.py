""" Process country data for merging user locations
"""

import pandas as pd

# See LICENSE.md for the license to the data files I am using here.

# Standard list of countries from the UN statistics division
# website: https://unstats.un.org/unsd/methodology/m49/overview
un_countries = pd.read_csv('un_stats_division_countries.csv')
un_countries = un_countries[['Country or Area', 'ISO-alpha3 Code']]
un_countries.columns = ['country_name', 'country_code']
# Fix UK and HKG country names
for (code, new_name) in (('GBR', 'United Kingdom'),
                         ('HKG', "China, Hong Kong SAR")):
    un_countries.at[
        un_countries['country_code'] == code,
        'country_name'] = new_name

# Variables as shortcuts
COUNTRY_NAMES = un_countries['country_name']
COUNTRY_CODES = un_countries['country_code']

# Read World bank GDP data, as downloaded from
# https://data.worldbank.org/indicator/NY.GDP.PCAP.CD
# License is CC-BY 4.0
gdp_per_cap = pd.read_csv('gdp_per_capita.csv', header=2)
gdp_per_cap = gdp_per_cap[['Country Code', '2017']]
gdp_per_cap.columns = ['country_code', 'gdp_per_cap']

# Population and other attributes of countries as downloaded from
# http://data.un.org/
pop_data = pd.read_csv('pop_surface.csv',
                       header=1,
                       thousands=',',
                       encoding='latin1')
# Get estimated mid-year population for 2018.
pop_2018 = pop_data[
    (pop_data['Year'] == 2018) &
    (pop_data['Series'] == 'Population mid-year estimates (millions)')]
pop_2018 = pop_2018[['Unnamed: 1', 'Value']]
pop_2018.columns = ['country_name', 'population']

# Merge all three country information tables into one.
country_data = un_countries.merge(pop_2018,
                                  on='country_name')
country_data = country_data.merge(gdp_per_cap,
                                  on='country_code')

# Write to main data file
country_data.to_csv('country_data.csv', index=False)
