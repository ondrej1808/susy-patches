# Supersymmetry 0.2.0.1-patch2 – osobní patche

Neoficiální opravy, které jsem si udělal **pro sebe** do modpacku
[Supersymmetry](https://github.com/SymmetricDevs/Supersymmetry) verze **0.2.0.1-patch2**.
Nejsou od autorů modů ani modpacku a nejsou nijak podporované. Používáš je na vlastní riziko,
před nasazením si zálohuj svět.

Patche se týkají dvou různých modů, proto jsou ve dvou forcích. Tohle repo je jen rozcestník:
README, soubory `.patch` a hotové jary (v Releases).

## Verze

| Mod | Verze v modpacku (původní) | Upstream zdroj | Patchnutá verze | Změny proti původní |
|-----|----------------------------|----------------|-----------------|---------------------|
| GregTech CEu | `gregtech-1.12.2-2.8.10-beta.jar` | [GregTechCEu/GregTech @ `v2.8.10`](https://github.com/GregTechCEu/GregTech/tree/v2.8.10) | [ondrej1808/GregTech @ `susy-0.2.0.1-patch2`](https://github.com/ondrej1808/GregTech/tree/susy-0.2.0.1-patch2) | [compare v2.8.10…patch](https://github.com/ondrej1808/GregTech/compare/v2.8.10...susy-0.2.0.1-patch2) |
| Industrial Renewal | `IndustrialRenewal_1.12.2-0.21.8.jar` | [Cassiobsk8/Industrial_Renewal @ `f9389105`](https://github.com/Cassiobsk8/Industrial_Renewal/tree/f9389105) (větev `1.12.2`, verze 0.21.8) | [ondrej1808/Industrial_Renewal @ `susy-0.2.0.1-patch2`](https://github.com/ondrej1808/Industrial_Renewal/tree/susy-0.2.0.1-patch2) | [compare f9389105…patch](https://github.com/ondrej1808/Industrial_Renewal/compare/f9389105...susy-0.2.0.1-patch2) |

Susy-Core (`Susy-Core-0.2.5.jar`) ani nic jiného v modpacku se nemění.

## Co je opravené

### GregTech CEu 2.8.10 – Crafting Station
- **Vyhledávání** na záložce s připojenými inventáři: hledá podle názvu, `@modid` filtruje podle modu.
- **Kolečko myši** posouvá seznam o jeden řádek a už nebere itemy z nástrojových slotů ani ze dvou
  řádků úložiště. Sloty ve skryté záložce byly dřív pořád aktivní, takže na ně reagoval Mouse Tweaks.
- Výsledek receptu se spolehlivě ukáže po **importu z JEI/HEI** i po změně mřížky
  (upstream [#2285](https://github.com/GregTechCEu/GregTech/issues/2285)).
- Prázdné řádky v seznamu inventářů se správně odebírají.
- Build: RetroFuturaGradle 1.4.9 a launchwrapper 1.17.4, protože původní artefakty už nejdou stáhnout.

### Industrial Renewal 0.21.8 – Storage Rack / Storage Chest
- **Mizení itemů** při stavění racků na sebe a při jejich ničení: stack se přepočítá celý najednou
  a při rozbití se obsah přesune do zbylých pater, místo aby se vysypal nebo ztratil.
- Obsah racku se neztrácí při uložení nebo reloadu a staré savy se načtou správně.
- Rack i chest jde **otevřít shora**. Shora se položí jen stejný rack, aby šlo dál stavět patra.
- Chest GUI: **kolečko** nad sloty a **search**, který skočí na řádek se shodou (Enter skočí na další).
- Shift-klik s plným inventářem dá itemy na zem místo do voidu, GUI se zavře při změně stacku
  a rozbití racku už nerozbije sousední.

Podrobná analýza chyb a testovací scénáře jsou v
[PATCH_STORAGE_RACK.md](https://github.com/ondrej1808/Industrial_Renewal/blob/susy-0.2.0.1-patch2/PATCH_STORAGE_RACK.md).

## Instalace (Prism Launcher)
1. Instanci Supersymmetry 0.2.0.1-patch2 si zkopíruj (Prism → Copy) a zálohuj svět.
2. Ve složce `minecraft/mods` odeber `gregtech-1.12.2-2.8.10-beta.jar` a
   `IndustrialRenewal_1.12.2-0.21.8.jar`.
3. Vlož jary z [Releases](https://github.com/ondrej1808/susy-patches/releases):
   `gregtech-1.12.2-2.8.10-beta-susypatch.jar` a `IndustrialRenewal_1.12.2-0.21.8-susypatch.jar`.
4. Na serveru musí být stejné jary jako u klienta.

Na verzi patch2 je testované jen v singleplayeru.

## Build ze zdroje
```bash
# GregTech (JDK 17+ pro Gradle, Java 8 si stáhne toolchain)
git clone -b susy-0.2.0.1-patch2 https://github.com/ondrej1808/GregTech.git
cd GregTech && ./gradlew assemble -x spotlessCheck   # -> build/libs/gregtech-1.12.2-2.8.10-beta.jar

# Industrial Renewal (JDK 8, ForgeGradle 2.3)
git clone -b susy-0.2.0.1-patch2 https://github.com/ondrej1808/Industrial_Renewal.git
cd Industrial_Renewal && ./gradlew build              # -> build/libs/IndustrialRenewal_1.12.2-0.21.8.jar
```
Případně stačí aplikovat soubory z [`patches/`](patches) (`git am`) na upstream tag nebo commit z tabulky.

## Licence a autoři
- **GregTech CEu** © GregTechCEu a přispěvatelé, licence **LGPL-3.0**. Upravená verze je pod stejnou licencí.
- **Industrial Renewal** © Cassiobsk8, licence **CC BY-NC-SA 4.0**. Upravená verze je pod stejnou
  licencí, jen pro nekomerční použití.
- **Supersymmetry** © SymmetricDevs.

Všechna práva k původním modům patří jejich autorům. Tady jsou jen moje úpravy.
