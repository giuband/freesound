from solr import Solr, SolrException
from sounds.models import Sound
import logging
from django.conf import settings

logger = logging.getLogger("search")

def convert_to_solr_document(sound):
    logger.info("creating solr XML from sound %d" % sound.id)
    document = {}

    document["id"] = sound.id
    document["username"] = sound.user.username
    document["created"] = sound.created
    document["original_filename"] = sound.original_filename

    document["description"] = sound.description
    document["tag"] = [taggeditem.tag.name for taggeditem in sound.tags.all()]
    
    document["license"] = sound.license.name
    
    document["is_remix"] = bool(sound.sources.count())
    document["was_remixed"] = bool(sound.remixes.count())

    if sound.pack:
        document["pack"] = sound.pack.name
    
    document["is_geotagged"] = sound.geotag != None

    document["type"] = sound.type

    document["duration"] = sound.duration
    document["bitdepth"] = sound.bitdepth if sound.bitdepth != None else 0
    document["bitrate"] = sound.bitrate if sound.bitrate != None else 0
    document["samplerate"] = int(sound.samplerate)
    document["filesize"] = sound.filesize
    document["channels"] = sound.channels
    document["md5"] = sound.md5

    document["num_downloads"] = sound.num_downloads

    document["avg_rating"] = sound.avg_rating
    document["num_ratings"] = sound.num_ratings

    document["comment"] = [comment.comment for comment in sound.comments.all()]
    document["comments"] = sound.comments.count()

    document["waveform_path_m"] = sound.locations("display.wave.M.path")
    document["waveform_path_l"] = sound.locations("display.wave.L.path")
    document["spectral_path_m"] = sound.locations("display.spectral.M.path")
    document["spectral_path_l"] = sound.locations("display.spectral.L.path")
    document["preview_path"]    = sound.locations("preview.LQ.mp3.path")
    
    return document


def add_sound_to_solr(sound):
    logger.info("adding single sound to solr index")
    try:
        Solr(settings.SOLR_URL).add([convert_to_solr_document(sound)])
    except SolrException, e:
        logger.error("failed to add sound %d to solr index, reason: %s" % (sound.id, str(e)))


def add_sounds_to_solr(sounds):
    logger.info("adding multiple sounds to solr index")
    solr = Solr(settings.SOLR_URL)

    try:
        logger.info("creating XML")
        documents = map(convert_to_solr_document, sounds)
        logger.info("posting to Solr")
        solr.add(documents)
    except SolrException, e:
        logger.error("failed to add sound batch to solr index, reason: %s" % str(e))
    
    logger.info("optimizing solr index")
    solr.optimize()
    logger.info("done")


def add_all_sounds_to_solr(slice_size=4000):
    qs = Sound.objects.select_related("pack", "user", "license").filter(processing_state="OK", moderation_state="OK")
    num_sounds = qs.count()
    for i in range(0, num_sounds, slice_size):
        add_sounds_to_solr(qs[i:i+slice_size])