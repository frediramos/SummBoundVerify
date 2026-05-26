import logging

from .engine import angrEngine

logging.getLogger('angr').setLevel('ERROR')
logging.getLogger('cle').setLevel('ERROR')
