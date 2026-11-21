
from dames import Partie
from exceptions import ErreurDames


def lire_coup(texte):
    morceaux = texte.replace("-", " ").replace("x", " ").split()

    if len(morceaux) != 2:
        raise ValueError("tapez deux cases, par exemple c3 d4")

    return morceaux[0], morceaux[1]


def main():
    partie = Partie()
    print(partie.plateau)

    while partie.gagnant is None:
        texte = input(f"{partie.trait} > ")

        if texte.strip().lower() == "quitter":
            print("Partie abandonnée.")
            return 0

        try:
            depart, arrivee = lire_coup(texte)
            coup = partie.jouer(depart, arrivee)

            print(coup)
            print(partie.plateau)

        except (ErreurDames, ValueError) as erreur:
            print(f"Refusé : {erreur}")

    print(f"Les {partie.gagnant}s gagnent !")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
