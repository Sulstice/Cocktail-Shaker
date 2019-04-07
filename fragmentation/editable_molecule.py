#!/usr/bin/env python
#
# Runs R Group Converter for Library Creation
#
# ----------------------------------------------------------

# imports
# ---------
from rdkit import Chem
import ruamel.yaml as yaml

# Load datasources
# -------------
with open("datasources/R_Groups.yaml") as stream:
    try:
        R_GROUP_DATASOURCE = yaml.safe_load(stream)
        R_GROUPS = R_GROUP_DATASOURCE['R_Groups']
    except yaml.YAMLError as exc:
        print(exc)


class RaiseMoleculeError(Exception):

    __version_error_parser__ = 1.0
    __allow_update__ = False

    """

    Raise Molecule Error if for some reason we can't evaluate a SMILES, 2D, or 3D molecule.

    """
    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors

class RGroupMolObject(object):
    """

    This class is used to take in a molecule and replace any R groups with a one of the groups from the R-Group.

    """

    __version_parser__ = 1.0
    __allow_update__ = False

    def __init__(self, molecule=None):
        from molvs import Validator
        if molecule != None:
            self.molecule = molecule
            self.original_smiles = Chem.MolToSmiles(self.molecule)

            # Validation
            validator_format = '%(asctime)s - %(levelname)s - %(validation)s - %(message)s'
            self.validate = Validator(log_format=validator_format)

    def validate_smiles(self, smiles):
        """

        This method takes the smiles string and runs through the validation check of a smiles string.

        Arguments:
            self (Object): Class RGroupMolObject
            smiles (string): Smiles string that needs to be evaluated
        Returns:
            N / A

        Exceptions:
            RaiseMoleculeError (Exception): MolVs Stacktrace and the smiles string that failed.

        """

        # Use MolVS to validate the smiles to make sure enumeration and r group connections are correct
        # at least in the 1D Format.
        from molvs import validate_smiles as vs

        try:
            vs(smiles)
        except RaiseMoleculeError as RME:
            print ("Not a Valid Smiles, Please check the formatting: %s" % self.original_smiles)
            print ("MolVs Stacktrace %s" % RME)

    def validate_molecule(self, molecule=None):

        """

        This function will be used to validate molecule objects

        Arguments:
            self (Object): Class RGroupMolObject
            molecule (RDKit Object): Molecule object we need to sanitize.
        Returns:
            N / A

        Exceptions:
            RaiseMoleculeError (Exception): Raise the Raise Molcule Error if the molecule is not valid.

        TODO: Verify Sanitize molcule that the validation works
        """

        if not molecule:
            try:
                Chem.rdmolops.SanitizeMol(molecule)
            except RaiseMoleculeError as RME:
                print ("Not a valid molecule: %s" % RME)
            finally:
                return molecule

    def find_r_groups(self):

        """

        Find functional groups that ligand library loader supports

        :return:

        """

        pattern_payload = {}

        for key, value in R_GROUPS.items():
            pattern = Chem.MolFromSmarts(value[1])
            if self.molecule.GetSubstructMatches(pattern,uniquify=False):
                print ("Found Functional Group: %s | Pattern Count: %s" % (key,
                                                                           len(self.molecule.GetSubstructMatches(
                                                                               pattern,uniquify=False))))
                pattern_payload[key] = [value[0], value[1]]

        return pattern_payload

    def r_group_enumerator(self, patterns_found):

        """

        TODO: Do this faster than O(n)^2 as this algorithm is not the most efficient.
        """

        modified_molecules = []

        for key, value in patterns_found.items():
            smarts_mol = Chem.MolFromSmarts(value[1])
            for r_functional_group, r_data in R_GROUPS.items():
                # Skip redundacies if the r group is already matched.
                if r_data[1] == value[1]:
                    continue

                modified_molecule = Chem.ReplaceSubstructs(self.molecule, smarts_mol,
                                                          Chem.MolFromSmiles(r_data[0]), replaceAll=True)

                modified_molecules.append(modified_molecule[0])

        return modified_molecules

class FileWriter(object):

    """

    This object is used to manage file outputs dependent on the user of the file.

    TODO: Support SDF, Mol2, Mol, Smiles (TXT) File, FASTA

    """

    __version_parser__ = 1.0
    __allow_update__ = False


    def __init__(self, name, molecules, option, fragementation=None):
        self.molecules = molecules
        self.name = name
        self.option = option
        self.fragmentation = fragementation # Determines if they would like the SDF split into fragments.

        # Avoids the continuous "if" and "else" statements.
        option_decision = self.option + "_writer"
        method_to_call = getattr(FileWriter, option_decision)
        result = method_to_call(self)

    def sdf_writer(self):

        """

        Arguments:
             self (Object): Parameters to write the files.

        """

        if not self.fragmentation:
            writer = Chem.SDWriter(self.name + ".sdf")
            for i in self.molecules:
                writer.write(i)

            writer.close()
        else:
            file_count = 1
            writer = Chem.SDWriter(self.name + str(file_count) + ".sdf")
            for i in self.molecules:
                if writer.NumMols() == self.fragmentation:
                    writer.close()
                    file_count += 1
                    writer = Chem.SDWriter(self.name + str(file_count) + ".sdf")

                writer.write(i)

            writer.close()

    def txt_writer(self):

        """

        Arguments:
             self (Object): Parameters to write the files.

        """

        if not self.fragmentation:
            writer = Chem.SmilesWriter(self.name + ".txt")
            for i in self.molecules:
                writer.write(i)

            writer.close()
        else:
            file_count = 1
            writer = Chem.SmilesWriter(self.name + str(file_count) + ".txt")
            for i in self.molecules:
                if writer.NumMols() == self.fragmentation:
                    writer.close()
                    file_count += 1
                    writer = Chem.SmilesWriter(self.name + str(file_count) + ".txt")

                writer.write(i)

            writer.close()

if __name__ == "__main__":
        scaffold_molecule = RGroupMolObject(Chem.MolFromSmiles('c1cc(CCCO)ccc1'))
        patterns_found = scaffold_molecule.find_r_groups()
        modified_molecules =scaffold_molecule.r_group_enumerator(patterns_found=patterns_found)
        FileWriter("test", modified_molecules, "sdf", fragementation=1)
        FileWriter("test", modified_molecules, "txt")

