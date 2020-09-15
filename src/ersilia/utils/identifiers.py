"""Generate identifiers for entities that are relevant to Ersilia, such as compounds or proteins."""

import uuid
import datetime
from hashids import Hashids
from datetime import datetime
from Bio.SeqUtils.CheckSum import seguid
import rdkit.Chem as Chem


class IdentifierGenerator(object):

    def __init__(self):
        pass


class LongIdentifier(IdentifierGenerator):

    def __init__(self):
        super().__init__()

    @staticmethod
    def encode():
        """Get UUID code (long identifier)"""
        return str(uuid.uuid4())


class ShortIdentifier(IdentifierGenerator):

    def __init__(self):
        super().__init__()
        self.hashids = Hashids(salt = "ersilia is open source", alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")

    def encode(self):
        """Short identifier based on timestamp"""
        return str(self.hashids.encode(int(datetime.today().timestamp())))


class MoleculeIdentifier(IdentifierGenerator):

    def __init__(self):
        super().__init__()

    @staticmethod
    def encode(smiles):
        """Get InChIKey of compound based on SMILES string"""
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise Exception("The SMILES string: %s is not valid or could not be converted to an InChIKey" % smiles)
        inchi = Chem.rdinchi.MolToInchi(mol)[0]
        if inchi is None:
            raise Exception("Could not obtain InChI")
        inchikey = Chem.rdinchi.InchiToInchiKey(inchi)
        return inchikey


class ProteinIdentifier(IdentifierGenerator):

    def __init__(self):
        super().__init__()

    @staticmethod
    def encode(sequence):
        """Protein seguid checksum based on aminoacid sequence"""
        return str(seguid(sequence))