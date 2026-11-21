"""Le jeu de dames en objets : cases, pièces, plateau et partie.

Règles du jeu de dames international (plateau de 10 x 10), simplifiées : une seule prise par
coup (pas de rafle) et pas de règle de la majorité.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from exceptions import CoupInvalideError

COLONNES = "abcdefghij"
TAILLE = 10
DIAGONALES = [(1, 1), (-1, 1), (1, -1), (-1, -1)]


def adversaire(couleur: str) -> str:
    """La couleur de l'autre joueur."""
    return "noir" if couleur == "blanc" else "blanc"


# --- Étape 1 : la case ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Case:
    """Une case, de a1 à j10."""
    colonne: str
    ligne: int

    def __post_init__(self):
        if len(self.colonne) != 1 or self.colonne not in COLONNES:
            raise ValueError(f"colonne invalide : {self.colonne!r}")

        if not 1 <= self.ligne <= 10:
            raise ValueError(f"ligne invalide : {self.ligne!r}")

    @classmethod
    def depuis_nom(cls, nom: str) -> "Case":
        try:
            return cls(nom[0], int(nom[1:]))
        except (ValueError, IndexError):
            raise ValueError(f"nom de case invalide : {nom!r}") from None

    @property
    def est_noire(self) -> bool:
        return (COLONNES.index(self.colonne) + self.ligne) % 2 == 1

    def decaler(self, dc: int, dl: int) -> "Case | None":
        colonne = COLONNES.index(self.colonne) + dc
        ligne = self.ligne + dl

        if not (0 <= colonne < 10 and 1 <= ligne <= 10):
            return None

        return Case(COLONNES[colonne], ligne)

    def __str__(self) -> str:
        return f"{self.colonne}{self.ligne}"

def en_case(case: Case | str) -> Case:
    if isinstance(case, Case):
        return case
    return Case.depuis_nom(case)


def ordre(case: Case) -> tuple:
    return (case.ligne, COLONNES.index(case.colonne))
# --- Étape 2 : les pièces ------------------------------------------------------------------------

class Piece(ABC):
    COULEURS = ("blanc", "noir")
    LETTRE = "?"
    NOM = "pièce"
    FEMININ = False

    def __init__(self, couleur: str):
        if couleur not in self.COULEURS:
            raise ValueError(f"couleur invalide : {couleur!r}")
        self._couleur = couleur

    @property
    def couleur(self) -> str:
        return self._couleur

    @property
    def sens(self) -> int:
        return 1 if self.couleur == "blanc" else -1

    @property
    def symbole(self) -> str:
        return self.LETTRE.upper() if self.couleur == "blanc" else self.LETTRE.lower()

    def est_adverse(self, autre: "Piece | None") -> bool:
        return autre is not None and self.couleur != autre.couleur

    @abstractmethod
    def deplacements(self, case: Case, plateau: "Plateau") -> set[Case]:
        pass

    @abstractmethod
    def prises(self, case: Case, plateau: "Plateau") -> dict[Case, Case]:
        pass

    def promouvoir(self, case: Case) -> "Piece":
        return self

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.couleur!r})"

    def __str__(self) -> str:
        if self.FEMININ:
            adjectif = "blanche" if self.couleur == "blanc" else "noire"
        else:
            adjectif = self.couleur

        return f"{self.NOM} {adjectif}"


# --- Étape 3 : le plateau ------------------------------------------------------------------------
class Plateau:
    """Le plateau A des pièces (composition), rangées dans un dict privé case -> pièce."""

    def __init__(self):
        self._pieces: dict[Case, Piece] = {}

    @classmethod
    def depuis_dict(cls, pieces: dict[str, str]) -> "Plateau":
        """Constructeur alternatif : Plateau.depuis_dict({"c3": "P", "f6": "d"}).
        P = pion, D = dame ; majuscule pour les blancs, minuscule pour les noirs."""
        plateau = cls()
        for nom, lettre in pieces.items():
            couleur = "blanc" if lettre.isupper() else "noir"
            classe = Pion if lettre.upper() == "P" else Dame
            plateau.placer(nom, classe(couleur))
        return plateau

    @classmethod
    def position_initiale(cls) -> "Plateau":
        plateau = cls()

        for ligne in range(1, 5):
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                if case.est_noire:
                    plateau.placer(case, Pion("blanc"))

        for ligne in range(7, 11):
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                if case.est_noire:
                    plateau.placer(case, Pion("noir"))

        return plateau

    def placer(self, case: "Case | str", piece: Piece) -> None:
        case = en_case(case)

        if not case.est_noire:
            raise ValueError("impossible de placer une pièce sur une case blanche")

        if case in self._pieces:
            raise ValueError(f"case déjà occupée : {case}")

        self._pieces[case] = piece
    def __getitem__(self, case: "Case | str") -> "Piece | None":
        return self._pieces.get(en_case(case))

    def __contains__(self, case: "Case | str") -> bool:
        return en_case(case) in self._pieces

    def __len__(self) -> int:
        return len(self._pieces)

    def __iter__(self):
        """Parcourt les cases occupées, ligne par ligne, de gauche à droite."""
        return iter(sorted(self._pieces, key=ordre))

    def compter(self, couleur: str) -> int:
        return sum(1 for case in self if self[case].couleur == couleur)

    # --- Étape 6

    def prises_possibles(self, couleur: str) -> dict[Case, dict[Case, Case]]:
        resultat = {}

        for case in self:
            piece = self[case]

            if piece.couleur == couleur:
                prises = piece.prises(case, self)
                if prises:
                    resultat[case] = prises

        return resultat


    def coups_possibles(self, couleur: str) -> list[tuple[Case, Case]]:
        prises = self.prises_possibles(couleur)

        if prises:
            coups = [
                (depart, arrivee)
                for depart, destinations in prises.items()
                for arrivee in destinations
            ]
        else:
            coups = [
                (depart, arrivee)
                for depart in self
                for piece in [self[depart]]
                if piece.couleur == couleur
                for arrivee in piece.deplacements(depart, self)
            ]

        return sorted(coups, key=lambda coup: (ordre(coup[0]), ordre(coup[1])))



    def deplacer(self, depart: "Case | str", arrivee: "Case | str") -> "Piece | None":
        depart = en_case(depart)
        arrivee = en_case(arrivee)

        piece = self[depart]

        if piece is None:
            raise CoupInvalideError(
                depart, arrivee, "aucune pièce sur la case de départ"
            )

        prises = self.prises_possibles(piece.couleur)

        if prises and depart not in prises:
            raise CoupInvalideError(
                depart, arrivee, "la prise est obligatoire"
            )

        coups = self.coups_possibles(piece.couleur)

        if (depart, arrivee) not in coups:
            raison = "la prise est obligatoire" if prises else "déplacement interdit"
            raise CoupInvalideError(depart, arrivee, raison)

        case_prise = piece.prises(depart, self).get(arrivee)
        piece_prise = None

        del self._pieces[depart]

        if case_prise is not None:
            piece_prise = self._pieces.pop(case_prise)

        self._pieces[arrivee] = piece.promouvoir(arrivee)

        return piece_prise

    # --- Étape 8
    def vers_dict(self) -> dict[str, str]:
        """L'inverse de depuis_dict : {"c3": "P", "f6": "d", ...}, dans l'ordre du plateau."""
        raise NotImplementedError("à compléter")

    # --- Affichage (fourni)
    def __repr__(self) -> str:
        return f"<Plateau : {self.compter('blanc')} blancs, {self.compter('noir')} noirs>"

    def __str__(self) -> str:
        lignes = []
        for ligne in range(TAILLE, 0, -1):
            cases = []
            for colonne in COLONNES:
                case = Case(colonne, ligne)
                piece = self[case]
                cases.append(piece.symbole if piece else "." if case.est_noire else " ")
            lignes.append(f"{ligne:>2}  " + " ".join(cases))
        lignes.append("    " + " ".join(COLONNES))
        return "\n".join(lignes)


# --- Étape 4 : le pion ---------------------------------------------------------------------------
class Pion(Piece):
    LETTRE = "P"
    NOM = "pion"
    FEMININ = False

    def deplacements(self, case: Case, plateau: "Plateau") -> set[Case]:
        resultat = set()

        for dc in (-1, 1):
            destination = case.decaler(dc, self.sens)
            if destination is not None and plateau[destination] is None:
                resultat.add(destination)

        return resultat

    def prises(self, case: Case, plateau: "Plateau") -> dict[Case, Case]:
        resultat = {}

        for dc in (-1, 1):
            for dl in (-1, 1):
                milieu = case.decaler(dc, dl)
                destination = case.decaler(2 * dc, 2 * dl)

                if milieu is None or destination is None:
                    continue

                piece = plateau[milieu]

                if self.est_adverse(piece) and plateau[destination] is None:
                    resultat[destination] = milieu

        return resultat

    def promouvoir(self, case: Case) -> Piece:
        if (self.couleur == "blanc" and case.ligne == 10) or (
            self.couleur == "noir" and case.ligne == 1
        ):
            return Dame(self.couleur)

        return self

# --- Étape 5 : la dame ---------------------------------------------------------------------------
class Dame(Piece):
    LETTRE = "D"
    NOM = "dame"
    FEMININ = True

    def deplacements(self, case: Case, plateau: "Plateau") -> set[Case]:
        resultat = set()

        for dc, dl in DIAGONALES:
            destination = case.decaler(dc, dl)

            while destination is not None and plateau[destination] is None:
                resultat.add(destination)
                destination = destination.decaler(dc, dl)

        return resultat

    def prises(self, case: Case, plateau: "Plateau") -> dict[Case, Case]:
        resultat = {}

        for dc, dl in DIAGONALES:
            destination = case.decaler(dc, dl)

            while destination is not None and plateau[destination] is None:
                destination = destination.decaler(dc, dl)

            if destination is None:
                continue

            piece = plateau[destination]

            if not self.est_adverse(piece):
                continue

            arrivee = destination.decaler(dc, dl)

            while arrivee is not None and plateau[arrivee] is None:
                resultat[arrivee] = destination
                arrivee = arrivee.decaler(dc, dl)

        return resultat


# --- Étape 7 : la partie -------------------------------------------------------------------------
@dataclass(frozen=True)
class Coup:
    """Un coup joué. Gelé : un coup joué ne change plus."""
    numero: int
    couleur: str
    depart: str
    arrivee: str
    prise: bool = False

    def __str__(self) -> str:
        separateur = "x" if self.prise else "-"
        return f"{self.numero}. {self.depart}{separateur}{self.arrivee}"


class Partie:
    """Une partie A un plateau et un historique (composition) et sait à qui c'est le tour."""

    def __init__(self, plateau: "Plateau | None" = None):
        self.plateau = plateau if plateau is not None else Plateau.position_initiale()
        self.trait = "blanc"
        self.historique: list[Coup] = []

    def jouer(self, depart: str, arrivee: str) -> Coup:
        piece = self.plateau[depart]

        if piece is not None and piece.couleur != self.trait:
            raise CoupInvalideError(
                depart,
                arrivee,
                f"c'est aux {self.trait}s de jouer"
                if self.trait == "blanc"
                else "c'est aux noirs de jouer",
            )

        couleur = self.trait
        prise = self.plateau.deplacer(depart, arrivee)

        coup = Coup(
            numero=len(self.historique) + 1,
            couleur=couleur,
            depart=str(en_case(depart)),
            arrivee=str(en_case(arrivee)),
            prise=prise is not None,
        )

        self.historique.append(coup)
        self.trait = adversaire(self.trait)

        return coup

    @property
    def gagnant(self) -> "str | None":
        if self.plateau.coups_possibles(self.trait):
            return None
        return adversaire(self.trait)

    # --- Étape 8
    def sauvegarder(self, chemin) -> None:
        """Écrit la partie en JSON : {"trait": ..., "pieces": {"c3": "P", ...}}."""
        raise NotImplementedError("à compléter")

    @classmethod
    def charger(cls, chemin) -> "Partie":
        """Constructeur alternatif : recrée une partie écrite par sauvegarder."""
        raise NotImplementedError("à compléter")
