# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 21:47:27 2026


"""

#Import needed packages 
import numpy as np
import nibabel as nib 
import dash 
from dash import dcc, html
from dash.dependencies import Input, Output 
import plotly.graph_objects as go 
from skimage.measure import marching_cubes
from scipy import ndimage


#set path and load data
NIFTI_PATH = r"load_your_path"


print("1. loads file") 
nii_img = nib.load(NIFTI_PATH) 
volume = nii_img.get_fdata()


#PREP data
if len(volume.shape) == 4: # nii file has 4 Dimensions, so we need to put no 4 on 0 
    volume = volume[:, :, :, 0]


# Downsampling 
volume = volume[::2, ::2, ::2]


# Normalisation
volume = (volume - np.min(volume)) / (np.max(volume) - np.min(volume))


# SKULL STRIPPING
print("2. skull stripping")

# create mask, everything above 0.34 is excluded (skin, hair, etc, we only want brain tissue)
tissue_mask = volume > 0.34

# erode mask
eroded_mask = ndimage.binary_erosion(tissue_mask, iterations=2)

# isolate the biggest object, which should be the brain
label_im, nb_labels = ndimage.label(eroded_mask)
sizes = ndimage.sum(eroded_mask, label_im, range(nb_labels + 1))
largest_label = np.argmax(sizes[1:]) + 1
brain_mask = (label_im == largest_label)

# bring the mask back to its original size
brain_mask = ndimage.binary_dilation(brain_mask, iterations=2)
brain_mask = ndimage.binary_fill_holes(brain_mask)

# now we should have the brain only
brain_stripped = np.where(brain_mask, volume, 0)
max_z = brain_stripped.shape[2] 


# Check if it has worked!!!! if not the cutoff value (here .34) has to be adjusted) 

app = dash.Dash(__name__) 

#Header
app.layout = html.Div([
    html.H1("Data Handling Abschlussprojekt, 3D Brain", style={'textAlign': 'center', 'fontFamily': 'Arial', 'color': 'white'}),
    
    html.Div([ #layout box
        html.Div([
            html.H3("Brain Segments"),
            html.P("Skull stripped, only brain tissue and spinal cord can be seen"), #text
            html.Br(), #Zeilenumbruch
            html.Label("Sagittale Schnitthöhe (Z-Achse):", style={'fontWeight': 'bold'}),
            dcc.Slider( #starts the slider to go through the brain slices
                id='slider', #Name the slider
                min=0, 
                max=max_z - 1, #max. value of slider
                value=max_z - 1,  #default for the beginning
                step=1,
                marks={i: {'label': str(i), 'style': {'color': 'white'}} for i in range(0, max_z, 10)}
            ),
            html.Br(),
            html.P("Steuerung: Klicken und ziehen zum Rotieren", 
                   style={'fontSize': '12px', 'color': 'gray', 'marginTop': '30px'})
        ], style={'width': '25%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '20px', 'backgroundColor': '#222', 'borderRadius': '10px', 'color': 'white'}),
       
       #new layout box
        html.Div([
            dcc.Graph(id='brain-mesh-graph', style={'height': '82vh'}) #determines the size of the graphic
        ], style={'width': '70%', 'display': 'inline-block', 'paddingLeft': '20px'}) 
    ], style={'display': 'flex'}) #needed so that both boxes, control and brainy remain together accordingly
], style={'padding': '20px', 'backgroundColor': '#111', 'minHeight': '100vh'})

#slide functions
@app.callback( #tells the programm that we need this function
    Output('brain-mesh-graph', 'figure'), #sets the output, here the brain
    [Input('slider', 'value')] #sets the input, here the slider value
)
def update_3d_cut(z_limit): 
    cut_volume = brain_stripped.copy() #creates a copy of the brain so that potential errors in the rendering doesnt do damage 
    if z_limit < max_z - 1:
        cut_volume[:, :, z_limit+1:] = 0 
        
    if np.max(cut_volume) == 0:
        return go.Figure() # so that if the slider reaches 0 the entire setup doesnt get stuck. 

    try:
        verts, faces, normals, values = marching_cubes(cut_volume, level=0.25)
    except Exception:#safety net; if not enough tissue try-except catches that
        return go.Figure() 
    
   
    fig = go.Figure(data=[go.Mesh3d( 
        x=verts[:, 0],#mr coordinates for display
        y=verts[:, 2],
        z=max_z - verts[:, 1], 
        i=faces[:, 0], #tells plotly how the points have to be connected to create a smoother display/surface
        j=faces[:, 1],
        k=faces[:, 2],
        intensity=values,      # mr values
        colorscale='mrybm',    # turns it into colour
        opacity=1.0, 
        flatshading=False,     # create shadowing
        lighting=dict(ambient=0.4, diffuse=0.8, specular=0.3, roughness=0.4),
        lightposition=dict(x=100, y=100, z=100) #light for a nice display
    )])
    
    
    
    
    fig.update_layout(
        scene=dict( 
            xaxis=dict(visible=False), 
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode='data', #assures original proportions from mri
            bgcolor='black'
        ),
        margin=dict(l=0, r=0, b=0, t=0), 
        template='plotly_dark' #darkmode
    )
    
    return fig #should now look pretty

if __name__ == '__main__':
    print("\n[INFO] please copy&paste the link: http://127.0.0.1:8050/")
    app.run(debug=False, port=8050)
  
    
    
    
    
    
