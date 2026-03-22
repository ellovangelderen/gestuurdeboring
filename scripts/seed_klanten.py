"""Seed Martien's 50 klantcodes in de klanten tabel."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal, engine, Base
from app.admin.models import Klant

KLANTEN = [
    (1, "3D", "3D-Drilling", "M.Visser", "logo_3D"),
    (2, "VB", "Verbree Boogzinkers", "M.Verbree", "Verbree_logo"),
    (3, "3D", "van Baarsen Buisleidingen", "M.Visser", "Baarsen_logo"),  # zelfde code als 3D
    (4, "HI", "Hogenhout", "A.Hogenhout", "logo_Hogenhout"),
    (5, "LI", "Liander", "W.Meijer", "logo_Liander"),
    (6, "RD", "RenD", "M.v.Hoolwerff", "logo_RenD"),
    (7, "DX", "Direxta", "S.Battaioui", "logo_direxta"),
    (8, "KB", "Kappert Boogzinkers", "A.Kappert", "logo_kappert"),
    (9, "VV", "VTV", "H.vd.Bighelaar", "logo_VTV"),
    (10, "NV", "NeijhofVisser", "B.Neijhof", "logo_NeijhofVisser"),
    (11, "RR", "RovoR", "R.Bláha", "logo_Rovor"),
    (12, "CN", "Circet Nederland", "T.v.Rooten", "logo_Circet"),
    (13, "AR", "Artemis", "E.Chatzidaki", "logo_Artemis"),
    (14, "EI", "Eljes", "H.Heiwegen", "logo_Eljes"),
    (15, "HG", "Heuvel", "D.Schafrat", "logo_Heuvel"),
    (16, "VG", "Van Gelder", "R.Aouragh", "logo_VanGelder"),
    (17, "VW", "VWTelecom", "M.v.Donselaar", "logo_VWT"),
    (18, "BI", "BAM Infra", "G.Kranenburg", "logo_BAM"),
    (19, "DE", "Dmissi Energy", "D.Brijder", "logo_DE"),
    (20, "AH", "a.hak", "T.Peeman", "logo_ahak"),
    (21, "RA", "APK", "T.vd Sloot", "logo_apk"),
    (22, "MK", "MKC", "F.Kleijn", "logo_MKC"),
    (23, "MI", "MIR Infratechniek", "Ali (MIR)", "MIR_logo"),
    (24, "VU", "VanVulpen", "N.Slagboom", "logo_vanVulpen"),
    (25, "PZ", "Polderzon", "F.v.Pelt", "logo_polderzon"),
    (26, "VS", "VSH", "L.Gorman", "logo_VSH"),
    (30, "BT", "BTL", "P.Visscher", "logo_BTLdrilling"),
    (31, "TM", "TM", "E.Heijnekamp", "logo_Tmtechniek"),
    (32, "TI", "Talsma Infra", "S.Talsma", "logo_Talsma"),
    (33, "QG", "Quint&vanGinkel", "A.Mikic", "logo_QuintvG"),
    (34, "EN", "Euronet", "N.Japenga", "logo_Euronet"),
    (35, "BH", "Bruton Boortechniek", "A.Hogenhout", "logo_Bruton"),
    (36, "FU", "Fiberunie", "A.Beelen", "logo_Fiberunie"),
    (37, "MT", "MHT", "F.Mouhout", "logo_MHT"),
    (38, "KK", "KorfKB", "K.Korf", "logo_KorfKB"),
    (39, "HV", "HVI Infra", "B.Hamers", "logo_HVI"),
    (40, "FS", "FUES", "R.Düztepe", "logo_FUES"),
    (41, "CC", "C&C", "G.Peker", "logo_C&C"),
    (42, "DI", "Darico", "B.Verweij", "logo_DI"),
    (43, "BA", "BAAS", "L.d.Dulk", "logo_BA"),
    (44, "IK", "InfraKennis", "K.Yilmaz", "Logo_InfraKennis"),
    (45, "GG", "Generation Green", "E.vd.Vlist", "logo_GG"),
    (46, "PK", "Peek", "R.Entrop", "logo_PK"),
    (47, "DM", "DMMB", "R.Wit", "logo_dmmb"),
    (48, "HN", "Hanab", "R.Kaman", "logo_HN"),
    (49, "FB", "FonsBakker", "E.Elsgeest", "logo_FB"),
]


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        toegevoegd = 0
        overgeslagen = 0
        for nr, code, naam, contact, logo in KLANTEN:
            # Nr 3 (van Baarsen) gebruikt code "3D" — maak uniek
            if nr == 3:
                code = "VB3"  # van Baarsen via 3D
            existing = db.query(Klant).filter_by(code=code).first()
            if existing:
                overgeslagen += 1
                continue
            db.add(Klant(nr=nr, code=code, naam=naam, contact=contact, logo_bestand=logo))
            toegevoegd += 1
        db.commit()
        print(f"Klanten: {toegevoegd} toegevoegd, {overgeslagen} overgeslagen")
        print(f"Totaal in DB: {db.query(Klant).count()}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
