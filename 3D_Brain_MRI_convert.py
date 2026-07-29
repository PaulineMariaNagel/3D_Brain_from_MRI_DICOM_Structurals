# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 21:47:27 2026


"""

#Import needed packages 
import numpy as np
import nibabel as nib # we need this because we have a nii.gz file
import dash # need that for the dashboard later on
from dash import dcc, html #self explanatory, schieberregler und layout zeugs
from dash.dependencies import Input, Output #verbindet regler mit grafik
import plotly.graph_objects as go # 3d grafik paket
from skimage.measure import marching_cubes #algorithmus der aus pixeln eine 3d oberfläche macht
from scipy import ndimage # bildverarbitung


#set path and load data
NIFTI_PATH = r"C:\Users\pauli\OneDrive\Desktop\65924614.nii.gz"


print("1. loads file") 
nii_img = nib.load(NIFTI_PATH) # nifti plus meta data
volume = nii_img.get_fdata() #only imaging data as 3d matrix


#PREP data
if len(volume.shape) == 4: # nii file hat 4 dimensionen, so needed to put no 4 on 0 
    volume = volume[:, :, :, 0]


# Downsampling as of lots of data, jeder 2 pixel in jede richtung
volume = volume[::2, ::2, ::2]


# Normalisieren, dunkelster punkt = 0, hellster = 1
volume = (volume - np.min(volume)) / (np.max(volume) - np.min(volume))


# SKULL STRIPPING (in zukunft mit fsl oder matlab)
print("2. skull stripping")

# Schritt A: Gewebe-Maske erstellen (Schwellenwert leicht angehoben), alles was dunkler ist als 0.34 fliegt raus (haut etc oft dunkler)
tissue_mask = volume > 0.34

# Schritt B: Gewebe wegschälen
eroded_mask = ndimage.binary_erosion(tissue_mask, iterations=2)

# Schritt C: Größtes Objekt isolieren, weil biggest object is the brainy (hopefully)
label_im, nb_labels = ndimage.label(eroded_mask)
sizes = ndimage.sum(eroded_mask, label_im, range(nb_labels + 1))
largest_label = np.argmax(sizes[1:]) + 1
brain_mask = (label_im == largest_label)

# Schritt D: Maske wieder auf Originalgröße bringen und Löcher im Inneren füllen
brain_mask = ndimage.binary_dilation(brain_mask, iterations=2)
brain_mask = ndimage.binary_fill_holes(brain_mask)

# Das final bereinigte Gehirn
brain_stripped = np.where(brain_mask, volume, 0)
max_z = brain_stripped.shape[2] 





#DEFNITELY DO CHECK BECAUSE ITS TRIAL AND ERROR

app = dash.Dash(__name__) #Initialisiert Web Dashboard

#Header
app.layout = html.Div([
    html.H1("Data Handling Abschlussprojekt, 3D Brain", style={'textAlign': 'center', 'fontFamily': 'Arial', 'color': 'white'}),
    
    html.Div([ #Öffnet eine neue Layout box links, brauchen wir für die Steuerung und den Schieber
        html.Div([
            html.H3("Brain Segments"),
            html.P("Skull stripped, only brain tissue and spinal cord can be seen"), #html P fügt einfach fließtext ein
            html.Br(), #Zeilenumbruch
            html.Label("Sagittale Schnitthöhe (Z-Achse):", style={'fontWeight': 'bold'}),
            dcc.Slider( #startet bzw setzt de schieberregler auf
                id='slider', #Name the slider
                min=0, 
                max=max_z - 1, #max. wert wo man die "oberste Scicht vom hirn sehen kann"
                value=max_z - 1,  #default wenn man ete öffnet, sodass das ganze hirn am anfang zu sehen ist
                step=1,
                marks={i: {'label': str(i), 'style': {'color': 'white'}} for i in range(0, max_z, 10)}#mini schleife, erstellt 10er markierungen beim slider
            ),
            html.Br(),
            html.P("Steuerung: Klicken und ziehen zum Rotieren", 
                   style={'fontSize': '12px', 'color': 'gray', 'marginTop': '30px'})
        ], style={'width': '25%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '20px', 'backgroundColor': '#222', 'borderRadius': '10px', 'color': 'white'}),
       #letze zeile schließt das kleine layout fenster, gesetzt das 25% vom gesamten bildschirm einnimmt, runde ecken und weiße schrift
        
        
        
        
        
        #nochmal neue layout box 
        html.Div([
            dcc.Graph(id='brain-mesh-graph', style={'height': '82vh'}) #fügt das grafikfenster ein, 82vh zwingt es dass 82% fensterhöhe
        ], style={'width': '70%', 'display': 'inline-block', 'paddingLeft': '20px'}) #schließt die box wieder, nimmt 70% vom bildschirm ein, 20pixel abstand zu steuerung
    ], style={'display': 'flex'}) #needed so that both boxes, control and brainy remain together accordingly
], style={'padding': '20px', 'backgroundColor': '#111', 'minHeight': '100vh'})
#schließt die Hauptbox, formatiert Innenabstand, bacground colour und sorgt dafür dass die seite so hoch wie der ganze bildschirm ist


#Stuff to slide
@app.callback( #sagt programm dass die Funktion automatisch aufgerufen werden soll
    Output('brain-mesh-graph', 'figure'), #bestimmt ziel, nämlich 3d brainy
    [Input('slider', 'value')] # bestimmt den auslöser, nämlich den schieberregler
)
def update_3d_cut(z_limit): #phyton function; startet funktion und übergibt schieber position als variable z_limit
    cut_volume = brain_stripped.copy() #erstellt kopie vom mr datensatz damit das original nicht kaputt geht beim rendering
    if z_limit < max_z - 1:
        cut_volume[:, :, z_limit+1:] = 0 #wenn der slider nach unten bewegt wird, werden alle brain slices darüber auf 0 gesetzt. 
        
    if np.max(cut_volume) == 0:
        return go.Figure() #damit nichts abstürtzt (man lernt ausfehlern), wird wenn der regler auf 0 ist die leere Grafik angezeigt

    try:
        verts, faces, normals, values = marching_cubes(cut_volume, level=0.25)
    except Exception:#safety net; if not enough tissue try-except catches that
        return go.Figure() 
    
   
    fig = go.Figure(data=[go.Mesh3d( #startet neue grafik
        x=verts[:, 0],#mr koordinaten
        y=verts[:, 2],
        z=max_z - verts[:, 1], #z ist gespiegelt weil brainy falsch stand
        i=faces[:, 0], #teilt plotly mit wie die punkte miteinander zu dreiecken verbunden werden müssen damit wir eine smoothe oberfläche haben
        j=faces[:, 1],
        k=faces[:, 2],
        intensity=values,      # mr signalwerte (Helligkeitswerte)
        colorscale='mrybm',    # turns it into colour
        opacity=1.0, #blickdichtes brainy
        flatshading=False,     #leichte schattierung damit realistisch
        lighting=dict(ambient=0.4, diffuse=0.8, specular=0.3, roughness=0.4),
        lightposition=dict(x=100, y=100, z=100) #richtet virtuelle scheinwerfer ein damit wir was sehen können
    )])
    
    
    
    
    fig.update_layout(
        scene=dict( #startet die 3d szene (würfel in dem brainy liegen soll)
            xaxis=dict(visible=False), 
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode='data', #assures original proportions from mri
            bgcolor='black'
        ),
        margin=dict(l=0, r=0, b=0, t=0), #ränder auf null damit grafik viel platz hat
        template='plotly_dark' #darkmode
    )
    
    return fig #should now look pretty

if __name__ == '__main__':
    print("\n[INFO] please copy&paste the link: http://127.0.0.1:8050/")
    app.run(debug=False, port=8050)
  
    
    
    
    
    