# ohgee
The OhGee Cloud Services Avatar
A robot that understand speech and face sentiment; it nods, speaks and uses an RGB LED heart to interact with observers.

Ohgee performs local motion detection, sound detection and speech synthesis.

When motion is detected, images are sent to the [Google Cloud Vision service](https://cloud.google.com/vision/) for object detection and labelling.

When sound is detected, the audion stream is sent to the [Google Cloud Speech-to-Text service](https://cloud.google.com/speech-to-text/) for speech recognition.

Any speech transcript returned by the speech service is sent to the [Google Cloud Natural Language service](https://cloud.google.com/natural-language/) for analysis.

Analyzed speech is examined for known key phrases and patterns to which Ohgee selects a random response from an associated set of responses.

Analyzed images are examined for faces - if faces are found, Ohgee elides each face with a smiley illustrating their detected sentiment.

[![demo](http://img.youtube.com/vi/nX_inqaAzOI/0.jpg)](https://www.youtube.com/watch?v=nX_inqaAzOI&feature=youtu.be&hd=1 "Ohgee demo video")

Here's a ![quick demo](https://photos.app.goo.gl/vuvbeiLZ1jtlUJki1?raw=true "Demo")

Want to know more... look at the code!
