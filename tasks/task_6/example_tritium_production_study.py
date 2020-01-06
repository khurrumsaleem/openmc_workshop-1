#!/usr/bin/env python3

"""example_isotope_plot.py: plots few 2D views of a simple tokamak geometry with neutron flux."""

__author__      = "Jonathan Shimwell"

import openmc
import matplotlib.pyplot as plt
import os
from plotly.offline import download_plotlyjs, plot
from plotly.graph_objs import Scatter, Layout
from tqdm import tqdm


def make_materials_geometry_tallies(enrichment_fraction):

    #MATERIALS#

    breeder_material =     openmc.Material(1, "breeder_material") #Pb84.2Li15.8 with natural enrichment of Li6
    breeder_material.add_element('Pb', 84.2,'ao')
    breeder_material.add_nuclide('Li6', enrichment_fraction*15.8, 'ao')
    breeder_material.add_nuclide('Li7', (1.0-enrichment_fraction)*15.8, 'ao')
    breeder_material.set_density('atom/b-cm',3.2720171e-2) # around 11 g/cm3

    copper = openmc.Material(name='copper')
    copper.set_density('g/cm3', 8.5)
    copper.add_element('Cu', 1.0)

    eurofer = openmc.Material(name='eurofer')
    eurofer.set_density('g/cm3', 7.75)
    eurofer.add_element('Fe', 89.067, percent_type='wo')
    eurofer.add_element('C', 0.11, percent_type='wo')
    eurofer.add_element('Mn', 0.4, percent_type='wo')
    eurofer.add_element('Cr', 9.0, percent_type='wo')
    eurofer.add_element('Ta', 0.12, percent_type='wo')
    eurofer.add_element('W', 1.1, percent_type='wo')
    eurofer.add_element('N', 0.003, percent_type='wo')
    eurofer.add_element('V', 0.2, percent_type='wo')

    mats = openmc.Materials([breeder_material, eurofer, copper])


    #GEOMETRY#

    central_sol_surface = openmc.ZCylinder(r=100)
    central_shield_outer_surface = openmc.ZCylinder(r=110)
    vessel_inner = openmc.Sphere(r=500)
    first_wall_outer_surface = openmc.Sphere(r=510)
    breeder_blanket_outer_surface = openmc.Sphere(r=610,boundary_type='vacuum')

    central_sol_region = -central_sol_surface & -vessel_inner
    central_sol_cell = openmc.Cell(region=central_sol_region) 
    central_sol_cell.fill = copper

    central_shield_region = +central_sol_surface & -central_shield_outer_surface & -vessel_inner
    central_shield_cell = openmc.Cell(region=central_shield_region) 
    central_shield_cell.fill = eurofer

    inner_vessel_region = -vessel_inner & + central_shield_outer_surface
    inner_vessel_cell = openmc.Cell(region=inner_vessel_region) 

    first_wall_region = -first_wall_outer_surface & +vessel_inner
    first_wall_cell = openmc.Cell(region=first_wall_region) 
    first_wall_cell.fill = eurofer

    breeder_blanket_region = +first_wall_outer_surface & -breeder_blanket_outer_surface
    breeder_blanket_cell = openmc.Cell(region=breeder_blanket_region) 
    breeder_blanket_cell.fill = breeder_material
    breeder_blanket_cell.name = 'breeder_blanket'

    universe = openmc.Universe(cells=[central_sol_cell,central_shield_cell,inner_vessel_cell,first_wall_cell, breeder_blanket_cell])
    geom = openmc.Geometry(universe)


    #SIMULATION SETTINGS#

    sett = openmc.Settings()
    batches = 3
    sett.batches = batches
    sett.inactive = 0
    sett.particles = 5000
    sett.run_mode = 'fixed source'

    source = openmc.Source()
    source.space = openmc.stats.Point((350,0,0))
    source.angle = openmc.stats.Isotropic()
    source.energy = openmc.stats.Discrete([14e6], [1])
    sett.source = source

    #TALLIES#

    tallies = openmc.Tallies()

    cell_filter = openmc.CellFilter(breeder_blanket_cell)
    tbr_tally = openmc.Tally(2,name='TBR')
    tbr_tally.filters = [cell_filter]
    tbr_tally.scores = ['205'] # MT 205 is the (n,Xt) reaction where X is a wildcard, if MT 105 or (n,t) then some tritium production will be missed, for example (n,nt) which happens in Li7 would be missed
    tallies.append(tbr_tally)

    #RUN OPENMC #
    model = openmc.model.Model(geom, mats, sett, tallies)
    model.run()
    sp = openmc.StatePoint('statepoint.'+str(batches)+'.h5')

    tbr_tally = sp.get_tally(name='TBR')

    df = tbr_tally.get_pandas_dataframe()
    
    tbr_tally_result = df['mean'].sum()
    tbr_tally_std_dev = df['std. dev.'].sum()

    return {'enrichment_fraction':enrichment_fraction,
            'tbr_tally_result':tbr_tally_result, 
            'tbr_tally_std_dev':tbr_tally_std_dev}


results=[]
for enrichment_fraction in tqdm([0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]):
    results.append(make_materials_geometry_tallies(enrichment_fraction))

print(results)

# PLOTS RESULTS #
trace1= Scatter(x=[entry['enrichment_fraction'] for entry in results], 
                y=[entry['tbr_tally_result'] for entry in results],
                mode = 'lines',
                error_y= {'array':[entry['tbr_tally_std_dev'] for entry in results]},
                )

layout = {'title':'Tritium production as a function of Li6 enrichment',
          'xaxis':{'title':'Li6 enrichment fraction'},
          'yaxis':{'title':'TBR'}
         }
plot({'data':[trace1],
      'layout':layout},
      filename='tbr_study.html')