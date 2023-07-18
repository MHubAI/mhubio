from .Meta import Meta

# define common modality types
CT      = Meta(mod="CT")        # Computed Tomography
CBCT    = Meta(mod="CBCT")      # Cone Beam CT (Has DICOM a predefined modality value for cbct?))
MR      = Meta(mod="MR")        # Magnetic Resonance
RTDOSE  = Meta(mod="RTDOSE")    # Radiotherapy Dose
PX      = Meta(mod="PX")        # Panoramic X-Ray
XA      = Meta(mod="XA")        # X-Ray Angiography
SEG     = Meta(mod="SEG")       # Segmentation
US      = Meta(mod="US")        # Ultrasound
SM      = Meta(mod="SM")        # Slide Microscopy