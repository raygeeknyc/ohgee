# ohgee
The OhGee Cloud Services Avatar

A robot that understand speech and face sentiment; it nods, speaks and uses an RGB LED heart to interact with observers.

Ohgee performs local motion detection, sound detection and speech synthesis.

When motion is detected, images are sent to the [Google Cloud Vision service](https://cloud.google.com/vision/) for object detection and labelling.

When sound is detected, the audion stream is sent to the [Google Cloud Speech-to-Text service](https://cloud.google.com/speech-to-text/) for speech recognition.

Any speech transcript returned by the speech service is sent to the [Google Cloud Natural Language service](https://cloud.google.com/natural-language/) for analysis.

Analyzed speech is examined for known key phrases and patterns to which Ohgee selects a random response from an associated set of responses.

Analyzed images are checked for some known labels, if any of those labels are present, Ohgee responds with both incredible wit and tact!
The analyzed images are examined for faces - if any faces are found, Ohgee elides each face with a smiley illustrating their detected sentiment.
If a face is "close enough" Ohgee greets the person and bid them farewell when they depart.

![In a nutshell](ohgee-one-page.png?raw=true "Overview")

Click on the image to see a quick demo...
[![demo](https://lh3.googleusercontent.com/T6kej9_cPDlSEd9RuixM6UfAnxD8Pn4kLtyg_F677h9dnkVcso314qCQtXiW7K5VIEyRATo-EFPbc4WX2Xl8VG_7bPn4D961hQTSD9dbOrtMporHQnpOHncr2e-oLg8B57IDEyb4fTmVGxK8vqjXDnppachEpghAH3_rr-hcVVWqQVJpJ8EI9cqRX13twzbzODYKb2m9ZLa4tdvgnOyym5mPU87Bz098QADv8DqgaEtCTxs4lVOE7mbAZgqv4X3G_z-o5e2ZVGOPvj13gdNQAJrl6GISkuVsPmTK9YQUE7L0rgLOD8FCmX1fvJfK4dMSyxmeDcyErcTAkwCfoN1EfWugtoMkxtkrq2eI3l7nl84x_Xu1XE5umZ1lpVeCL7C8wV6uaERk6ENYklICMdqmGo9Kg4edn3tR7eVIso6LTzdXxLSMMlhiEkCk36c_LmVHes6ZNrX_y9c9IywPydiaWsy7eIxX-x3URVtep3RRoR-y4uibEDoCx00TiWnEA84pk4Yw93SO8c77TGdXiIBbYC4RGvCKaMTD6SxxFg1AHUDhpNNLKqqaquGSkgJS_o8kgZtU542A-lmX8XxZobiCH2Amy83ybtX5pU8XUr0RnzDnPm74WPJFKchbByj6gc3p=s250-k-rw-no)](https://youtu.be/PBYmpuFzArQ "Ohgee demo")


But wait... there's more!

Since visual and audible "noise" varies widely based on location, Ohgee establishes background levels for sound and motion when starting up.

Ohgee also updates from github at startup and restarts if network connectivity is lost.

Want to know more about any of this? Look at the code!
