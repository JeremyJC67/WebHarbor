"""R18 informed verifier: eligible comparison OR global descending exclusion.

Ground truth is frozen inside this verifier, never supplied by the browsing agent.
Source catalog SHA256 inputs (147 unchanged movies + 123 additions):
aa04c6ac5acbaf76da631f120e82fad4d8f97eb7fa2e6b238b88c939f8f822e8
76e9ee372f85d08812cc0561e454c69e39e2fc803881adc7c98a78b2492160ca
A winner with no listed streaming date remains eligible; report that absence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import parse_qs, urlsplit

from contracts import CONTRACTS
from verify_lib import Run, Snapshot, VerificationError, heading, key, main_dom, movie_card, movie_links, require
from verify_3 import MONTH, dates, detail_date, detail_producers, leaf_texts, read_only
from verify_0 import missing_streaming_date_evidence

TASK_ID = 'RottenTomatoes--18'
SOURCE_FACTS_SHA256 = '51950cc069b5890b398c4c9a44de901d2a2583c3ded420ad8e167212d776e4a9'
FACTS = json.loads(r'''[
{"slug":"avengers_endgame","title":"Avengers: Endgame","producers":["Kevin Feige"],"audience_score":90,"date":"2019-07-30"},
{"slug":"avatar_fire_and_ash","title":"Avatar: Fire and Ash","producers":["James Cameron","Jon Landau"],"audience_score":90,"date":"2026-03-31"},
{"slug":"anaconda_2025","title":"Anaconda","producers":["Brad Fuller","Andrew Form","Kevin Etten","Tom Gormican"],"audience_score":74,"date":"2026-01-27"},
{"slug":"28_years_later_the_bone_temple","title":"28 Years Later: The Bone Temple","producers":["Danny Boyle","Alex Garland","Andrew Macdonald","Peter Rice","Bernard Bellew"],"audience_score":88,"date":"2026-02-17"},
{"slug":"blackberry","title":"BlackBerry","producers":["Niv Fichman","Matthew Miller","Fraser Ash","Kevin Krikst"],"audience_score":94,"date":"2023-06-02"},
{"slug":"shrek","title":"Shrek","producers":["Aron Warner","John H. Williams","Jeffrey Katzenberg"],"audience_score":90,"date":"2015-11-25"},
{"slug":"godzilla_minus_one","title":"Godzilla Minus One","producers":["Minami Ichikawa","Kazuaki Kishida","Keiichiro Moriya","Kenji Yamada"],"audience_score":98,"date":"2024-06-01"},
{"slug":"top_gun_maverick","title":"Top Gun: Maverick","producers":["Christopher McQuarrie","Jerry Bruckheimer","Tom Cruise","David Ellison"],"audience_score":99,"date":"2022-08-22"},
{"slug":"oddity","title":"Oddity","producers":["Laura Tunstall","Mette-Marie Kongsved","Katie Holly","Evan Horan"],"audience_score":85,"date":"2024-08-20"},
{"slug":"the_dark_knight","title":"The Dark Knight","producers":["Emma Thomas","Charles Roven"],"audience_score":94,"date":"2010-06-14"},
{"slug":"superman_2025","title":"Superman","producers":["Peter Safran","James Gunn"],"audience_score":90,"date":"2025-08-15"},
{"slug":"dune_part_two","title":"Dune: Part Two","producers":["Mary Parent","Cale Boyter","Denis Villeneuve","Tanya Lapointe","Patrick McCormick"],"audience_score":95,"date":"2024-04-16"},
{"slug":"inside_out_2","title":"Inside Out 2","producers":["Mark Nielsen"],"audience_score":94,"date":"2024-08-20"},
{"slug":"oppenheimer_2023","title":"Oppenheimer","producers":["Emma Thomas","Charles Roven","Christopher Nolan"],"audience_score":91,"date":"2023-11-21"},
{"slug":"barbie","title":"Barbie","producers":["David Heyman","Margot Robbie","Tom Ackerley","Robbie Brenner"],"audience_score":83,"date":"2023-09-12"},
{"slug":"everything_everywhere_all_at_once","title":"Everything Everywhere All at Once","producers":["Joe Russo","Anthony Russo","Mike Larocca","Daniel Kwan","Daniel Scheinert","Jonathan Wang"],"audience_score":79,"date":"2022-06-07"},
{"slug":"parasite_2019","title":"Parasite","producers":["Kwak Sin-ae","Moon Yanggwon"],"audience_score":90,"date":"2019-10-11"},
{"slug":"the_wild_robot","title":"The Wild Robot","producers":["Jeff Hermann"],"audience_score":98,"date":"2024-10-15"},
{"slug":"the_substance","title":"The Substance","producers":["Coralie Fargeat","Eric Fellner","Tim Bevan"],"audience_score":76,"date":"2024-10-31"},
{"slug":"deadpool_and_wolverine","title":"Deadpool & Wolverine","producers":["Kevin Feige","Ryan Reynolds","Shawn Levy","Lauren Shuler Donner"],"audience_score":94,"date":"2024-10-01"},
{"slug":"nosferatu_2024","title":"Nosferatu","producers":["Jeff Robinov","John Graham","Chris Columbus","Eleanor Columbus"],"audience_score":73,"date":"2025-01-21"},
{"slug":"interstellar_2014","title":"Interstellar","producers":["Emma Thomas","Lynda Obst"],"audience_score":87,"date":"2016-05-24"},
{"slug":"wicked_2024","title":"Wicked","producers":["Marc Platt","David Stone"],"audience_score":95,"date":"2024-12-31"},
{"slug":"sinners_2025","title":"Sinners","producers":["Ryan Coogler","Sev Ohanian","Zinzi Coogler"],"audience_score":96,"date":"2025-06-03"},
{"slug":"the_fantastic_four_first_steps","title":"The Fantastic Four: First Steps","producers":["Kevin Feige"],"audience_score":90,"date":"2025-09-23"},
{"slug":"lilo_and_stitch","title":"Lilo & Stitch","producers":["Clark Spencer"],"audience_score":78,"date":"2014-01-01"},
{"slug":"lifehack","title":"LifeHack","producers":["Timur Bekmambetov","Sasha Kletsov","Joann Kushner"],"audience_score":64,"date":"2026-08-04"},
{"slug":"obsession_2025","title":"Obsession","producers":["James Harris","Christian Mercuri","Haley Nicole Johnson","Roman Viaris"],"audience_score":94,"date":"2026-06-30"},
{"slug":"is_god_is","title":"Is God Is","producers":["Tessa Thompson","Kishori Rajan","Riva Marker","Janicza Bravo","Aleshea Harris"],"audience_score":89,"date":null},
{"slug":"the_wizard_of_the_kremlin","title":"The Wizard of the Kremlin","producers":["Olivier Assayas"],"audience_score":56,"date":"2026-06-16"},
{"slug":"drivers_ed","title":"Driver's Ed","producers":["Jonas Pate","Jennifer Pate","David Stone"],"audience_score":null,"date":"2026-05-15"},
{"slug":"magic_hour_2025_2","title":"Magic Hour","producers":["Emily A. Neumann"],"audience_score":null,"date":"2026-06-26"},
{"slug":"decorado_2025","title":"Decorado","producers":[],"audience_score":null,"date":"2026-07-07"},
{"slug":"forge_2025","title":"Forge","producers":["Damian Bao","Liz Daering-Glass","Gabrielle Cordero","Jing Ai Ng"],"audience_score":null,"date":null},
{"slug":"diamonds_2024","title":"Diamonds","producers":["Marco Belardi","Tilde Corsi"],"audience_score":null,"date":null},
{"slug":"top_gun","title":"Top Gun","producers":["Jerry Bruckheimer","Don Simpson"],"audience_score":83,"date":"2013-08-01"},
{"slug":"remarkably_bright_creatures","title":"Remarkably Bright Creatures","producers":["Bryan Unkeless","Peter Craig","David Levine"],"audience_score":90,"date":"2026-05-08"},
{"slug":"send_help","title":"Send Help","producers":["Zainab Azizi"],"audience_score":86,"date":"2026-03-24"},
{"slug":"project_hail_mary","title":"Project Hail Mary","producers":["Amy Pascal","Ryan Gosling","Phil Lord","Christopher Miller","Aditya Sood","Rachel O'Connor","Andy Weir"],"audience_score":95,"date":"2026-05-12"},
{"slug":"apex_2026","title":"Apex","producers":["Peter Chernin","Jenno Topping","David Ready","Ian Bryce","Charlize Theron","Beth Kono","A.J. Dix","Baltasar Kormákur"],"audience_score":46,"date":"2026-04-24"},
{"slug":"the_drama","title":"The Drama","producers":["Lars Knudsen","Ari Aster","Tyler Campellone"],"audience_score":78,"date":"2026-05-05"},
{"slug":"exit_8_2025","title":"Exit 8","producers":["Taichi Ito"],"audience_score":86,"date":"2026-05-08"},
{"slug":"the_perfect_neighbor_2025","title":"The Perfect Neighbor","producers":["Nikon Kwantu","Geeta Gandbhir","Alisa Payne","Sam Bisbee"],"audience_score":80,"date":"2025-10-17"},
{"slug":"the_punisher_one_last_kill","title":"The Punisher: One Last Kill","producers":[],"audience_score":79,"date":"2026-05-12"},
{"slug":"swapped_2026","title":"Swapped","producers":["John Lasseter","David Ellison","Dana Goldberg","Mary Ellen Bauder"],"audience_score":87,"date":"2026-05-01"},
{"slug":"mortal_kombat_2021","title":"Mortal Kombat","producers":["James Wan","Todd Garner"],"audience_score":85,"date":"2021-04-23"},
{"slug":"wuthering_heights_2026","title":"Wuthering Heights","producers":["Josey McNamara","Emerald Fennell","Margot Robbie","Tom Ackerley"],"audience_score":74,"date":"2026-03-31"},
{"slug":"hoppers","title":"Hoppers","producers":["Nicole Paradis Grindle"],"audience_score":93,"date":"2026-04-28"},
{"slug":"ready_or_not_2_here_i_come","title":"Ready or Not 2: Here I Come","producers":["Tripp Vinson","James Vanderbilt","William Sherak","Bradley J. Fischer"],"audience_score":88,"date":"2026-05-05"},
{"slug":"gary_2026","title":"Gary","producers":[],"audience_score":67,"date":"2026-05-05"},
{"slug":"the_devil_wears_prada","title":"The Devil Wears Prada","producers":["Wendy Finerman"],"audience_score":76,"date":"2013-03-01"},
{"slug":"marty_supreme","title":"Marty Supreme","producers":["Eli Bush","Ronald Bronstein","Josh Safdie","Anthony Katagas","Timothée Chalamet"],"audience_score":82,"date":"2026-02-10"},
{"slug":"greenland_2_migration","title":"Greenland 2: Migration","producers":["Basil Iwanyk","Erica Lee","Gerard Butler","Alan Siegel","Sébastien Raybaud","John Zois","Brendon Boyea"],"audience_score":66,"date":"2026-01-27"},
{"slug":"a_great_awakening","title":"A Great Awakening","producers":["Steve Buckwalter","Troy Thorne"],"audience_score":97,"date":"2026-05-05"},
{"slug":"beast_2026","title":"Beast","producers":["John Schwarz","David Frigerio","Michael Schwarz","Tim O'Hair"],"audience_score":74,"date":"2026-05-08"},
{"slug":"good_luck_have_fun_dont_die","title":"Good Luck, Have Fun, Don't Die","producers":["Gore Verbinski","Robert Kulzer","Erwin Stoff","Oliver Obst","Denise Chamian"],"audience_score":84,"date":"2026-03-10"},
{"slug":"the_housemaid_2025","title":"The Housemaid","producers":["Todd Lieberman","Laura Allen Fischer","Paul Feig","Carly Kleinbart"],"audience_score":92,"date":"2026-02-03"},
{"slug":"crime_101_2026","title":"Crime 101","producers":["Eric Fellner","Tim Bevan","Shane Salerno","Chris Hemsworth","Bart Layton","Dimitri Doganis","Derrin Schlesinger","Benjamin Grayson"],"audience_score":83,"date":"2026-04-01"},
{"slug":"they_will_kill_you","title":"They Will Kill You","producers":["David Ellison","Dana Goldberg","Don Granger","Andy Muschietti","Barbara Muschietti","Dan Kagan"],"audience_score":76,"date":"2026-04-28"},
{"slug":"we_bury_the_dead","title":"We Bury the Dead","producers":["Ross M. Dinerstein","Mark Fasano","Joshua Harris","Kelvin Munro","Grant Sputore"],"audience_score":45,"date":"2026-02-03"},
{"slug":"good_boy_2025","title":"Good Boy","producers":["Kari Fischer"],"audience_score":81,"date":"2025-10-24"},
{"slug":"merrily_we_roll_along","title":"Merrily We Roll Along","producers":["Patrick Catullo","Sonia Friedman","Jon Kamen","F. Richard Pappas","David Sirulnick","David Babani"],"audience_score":95,"date":"2026-01-20"},
{"slug":"bugonia","title":"Bugonia","producers":["Ed Guiney","Andrew Lowe","Emma Stone","Ari Aster","Lars Knudsen","Miky Lee","Jerry Kyoungboum Ko"],"audience_score":84,"date":"2025-11-25"},
{"slug":"mothers_day_2016","title":"Mother's Day","producers":["Mike Karz","Wayne Allan Rice","Daniel Diamond","Brandt Andersen","Howard Burd","Mark DiSalle"],"audience_score":43,"date":"2016-08-02"},
{"slug":"the_devil_wears_prada_2","title":"The Devil Wears Prada 2","producers":["Wendy Finerman"],"audience_score":84,"date":"2026-06-30"},
{"slug":"hokum","title":"Hokum","producers":["Roy Lee","Steven Schneider","Derek Dauchy","Ruth Treacy","Julianne Forde"],"audience_score":82,"date":"2026-06-02"},
{"slug":"the_christophers","title":"The Christophers","producers":["Iain Canning","Jim Parks"],"audience_score":87,"date":"2026-05-12"},
{"slug":"fuze","title":"Fuze","producers":["Sébastien Raybaud","Callum Christopher Grant","David Mackenzie","Gillian Berrie"],"audience_score":78,"date":"2026-05-26"},
{"slug":"i_swear_2025","title":"I Swear","producers":["Piers Tempest","Kirk Jones","Georgia Bayliff"],"audience_score":98,"date":"2026-06-02"},
{"slug":"erupcja","title":"Erupcja","producers":["Pete Ohs","Charli XCX","Luke Arreguin","Jeremy O. Harris","Josh Godfrey"],"audience_score":null,"date":"2026-06-02"},
{"slug":"normal_2025","title":"Normal","producers":["Marc Provissiero","Derek Kolstad","Bob Odenkirk"],"audience_score":75,"date":"2026-05-19"},
{"slug":"blue_heron","title":"Blue Heron","producers":["Ryan Bobkin","Sara Wylie","Sophy Romvari","Gábor Osváth"],"audience_score":69,"date":"2026-06-23"},
{"slug":"the_stranger_2025","title":"The Stranger","producers":["François Ozon"],"audience_score":81,"date":"2026-05-19"},
{"slug":"amrum","title":"Amrum","producers":[],"audience_score":84,"date":"2026-06-02"},
{"slug":"miroirs_no_3","title":"Miroirs No. 3","producers":["Florian Koerner von Gustorf","Michael Weber","Anton Kaiser"],"audience_score":null,"date":"2026-05-19"},
{"slug":"mr_nobody_against_putin","title":"Mr. Nobody Against Putin","producers":["Helle Faber"],"audience_score":75,"date":"2026-01-22"},
{"slug":"the_blue_trail","title":"The Blue Trail","producers":["Rachel Daisy Ellis","Sandino Saravia Vinay"],"audience_score":92,"date":null},
{"slug":"two_prosecutors","title":"Two Prosecutors","producers":["Kevin Chneiweiss"],"audience_score":null,"date":"2026-05-26"},
{"slug":"kontinental_25","title":"Kontinental '25","producers":["Rodrigo Teixeira","Alexandru Teodorescu"],"audience_score":null,"date":"2026-05-26"},
{"slug":"tow_2025","title":"Tow","producers":["Brent Stiefel","Stephanie Laing","Samantha Nisenboim","Rose Byrne","Danyelle Foord","Josh Ricks"],"audience_score":63,"date":"2026-04-21"},
{"slug":"a_poet","title":"A Poet","producers":["Simón Mesa Soto","Juan Sarmiento G.","Manuel Ruiz Montealegre"],"audience_score":92,"date":"2026-03-24"},
{"slug":"late_shift_2025","title":"Late Shift","producers":["Reto Schärli","Lukas Hobi"],"audience_score":null,"date":"2026-04-21"},
{"slug":"put_your_soul_on_your_hand_and_walk","title":"Put Your Soul on Your Hand and Walk","producers":["Sepideh Farsi"],"audience_score":null,"date":"2025-12-16"},
{"slug":"the_sheep_detectives","title":"The Sheep Detectives","producers":["Lindsay Doran","Tim Bevan","Eric Fellner"],"audience_score":96,"date":"2026-06-24"},
{"slug":"marty_life_is_short","title":"Marty, Life Is Short","producers":["Sara Bernstein","Meredith Kaulfers","Christopher St. John","Lawrence Kasdan","Blair Foster"],"audience_score":92,"date":"2026-05-12"},
{"slug":"nuremberg_2025","title":"Nuremberg","producers":["Richard Saperstein","Bradley J. Fischer","William Sherak","Frank Smith","Benjamin Tappan","Cherilyn Hawrysh","István Major","George Freeman"],"audience_score":95,"date":"2025-12-23"},
{"slug":"train_dreams","title":"Train Dreams","producers":["Michael Heimler","Will Janowitz","Marissa McMahon","Ashley Schlaifer","Teddy Schwarzman"],"audience_score":91,"date":"2025-11-21"},
{"slug":"the_rip","title":"The Rip","producers":["Ben Affleck","Matt Damon","Luciana Damon","Dani Bernfeld","Michael Joe","Kevin Halloran"],"audience_score":65,"date":"2026-01-16"},
{"slug":"war_machine","title":"War Machine","producers":["Patrick Hughes","Todd Lieberman","Alexander Young","Greg McLean"],"audience_score":63,"date":"2026-03-06"},
{"slug":"peaky_blinders_the_immortal_man","title":"Peaky Blinders: The Immortal Man","producers":["Steven Knight","Cillian Murphy","Guy Heeley","Caryn Mandabach","Patrick Holland"],"audience_score":88,"date":"2026-03-20"},
{"slug":"striking_distance","title":"Striking Distance","producers":["Hunt Lowry","Arnon Milchan","Tony Thomopoulos"],"audience_score":35,"date":"2014-03-09"},
{"slug":"green_book","title":"Green Book","producers":["Jim Burke","Charles B. Wessler","Peter Farrelly","Brian Hayes Currie","Nick Vallelonga"],"audience_score":92,"date":"2019-02-19"},
{"slug":"domestic_disturbance","title":"Domestic Disturbance","producers":["Donald De Line","Jonathan D. Krane"],"audience_score":37,"date":"2017-01-01"},
{"slug":"people_we_meet_on_vacation","title":"People We Meet on Vacation","producers":["Marty Bowen","Wyck Godfrey","Isaac Klausner"],"audience_score":68,"date":"2026-01-09"},
{"slug":"relay","title":"Relay","producers":["Basil Iwanyk","Gillian Berrie","David Mackenzie","Teddy Schwarzman"],"audience_score":89,"date":"2025-09-16"},
{"slug":"thrash","title":"Thrash","producers":["Adam McKay","Kevin J. Messick"],"audience_score":24,"date":"2026-04-10"},
{"slug":"wake_up_dead_man_a_knives_out_mystery","title":"Wake Up Dead Man: A Knives Out Mystery","producers":["Rian Johnson","Ram Bergman"],"audience_score":93,"date":"2025-12-12"},
{"slug":"you_me_and_tuscany","title":"You, Me & Tuscany","producers":["Will Packer","Johanna Byer"],"audience_score":92,"date":"2026-05-12"},
{"slug":"faces_of_death_2026","title":"Faces of Death","producers":["Don Murphy","Susan Montford","Greg Gilreath","Adam Hendricks"],"audience_score":62,"date":"2026-05-12"},
{"slug":"suburban_fury","title":"Suburban Fury","producers":["Jason Reid","Zachariah Sebastian"],"audience_score":null,"date":"2026-05-12"},
{"slug":"spositions","title":"$POSITIONS","producers":["Ben Gojer","Jake Bloom","Brandon Daley"],"audience_score":null,"date":"2026-05-12"},
{"slug":"marc_by_sofia","title":"Marc by Sofia","producers":["Jane Cha","Sofia Coppola","R.J. Cutler","Elise Pearlstein","Trevor Smith"],"audience_score":null,"date":"2026-05-12"},
{"slug":"greenland","title":"Greenland","producers":["Gerard Butler","Basil Iwanyk","Sébastien Raybaud","Alan Siegel"],"audience_score":63,"date":"2021-01-26"},
{"slug":"the_running_man_2025","title":"The Running Man","producers":["Edgar Wright","Nira Park","Audrey Chon","Simon Kinberg"],"audience_score":77,"date":"2025-12-16"},
{"slug":"balls_up_2026","title":"Balls Up","producers":["David Ellison","Dana Goldberg","Don Granger","Andrew J. Muscato","Paul Wernick","Rhett Reese"],"audience_score":30,"date":"2026-04-15"},
{"slug":"mercy_2026","title":"Mercy","producers":["Charles Roven","Robert Amidon","Timur Bekmambetov","Majd Nassif"],"audience_score":81,"date":"2026-02-17"},
{"slug":"man_on_fire","title":"Man on Fire","producers":["Arnon Milchan","Lucas Foster","Tony Scott"],"audience_score":89,"date":"2013-03-01"},
{"slug":"mike_and_nick_and_nick_and_alice","title":"Mike & Nick & Nick & Alice","producers":["Andrew Lazar"],"audience_score":61,"date":"2026-03-27"},
{"slug":"mortal_kombat","title":"Mortal Kombat","producers":["Lawrence Kasanoff"],"audience_score":58,"date":"2009-09-01"},
{"slug":"shelter_2026","title":"Shelter","producers":["Jason Statham","John Friedberg","Brendon Boyea","Greg Silverman","Jon Berg"],"audience_score":87,"date":"2026-02-24"},
{"slug":"the_hunt_2019","title":"The Hunt","producers":["Damon Lindelof","Jason Blum"],"audience_score":66,"date":"2020-03-20"},
{"slug":"yes_2025","title":"Yes","producers":["Judith Lou Lévy","Hugo Sélignac","Antoine Lafon"],"audience_score":null,"date":"2026-05-12"},
{"slug":"goat_2026","title":"GOAT","producers":["Michelle Raimo","Steph Curry","Erick Peyton","Adam Rosenberg","Rodney Rothman"],"audience_score":92,"date":"2026-03-24"},
{"slug":"outcome","title":"Outcome","producers":["Jonah Hill","Matt Dines","Alison Goodwin"],"audience_score":30,"date":"2026-04-10"},
{"slug":"one_battle_after_another","title":"One Battle After Another","producers":["Paul Thomas Anderson","Adam Somner","Sara Murphy"],"audience_score":85,"date":"2025-11-14"},
{"slug":"buffet_infinity","title":"Buffet Infinity","producers":["Simon Glassman","Michael Peterson"],"audience_score":null,"date":"2026-05-08"},
{"slug":"rental_family","title":"Rental Family","producers":["Eddie Vaisman","Julia Lebedev","HIKARI","Shin Yamaguchi"],"audience_score":95,"date":"2026-01-13"},
{"slug":"fantasy_life","title":"Fantasy Life","producers":["Charlie Alderman","Christopher Dodds","Amanda Peet","Phil Keefe","Emily McCann Lesser","David Bernon","Sam Slater"],"audience_score":65,"date":"2026-05-08"},
{"slug":"undertone","title":"undertone","producers":["Cody Calahan","Dan Slater"],"audience_score":50,"date":"2026-04-14"},
{"slug":"dust_bunny","title":"Dust Bunny","producers":["Basil Iwanyk","Erica Lee","Bryan Fuller"],"audience_score":82,"date":"2026-01-13"},
{"slug":"hallow_road","title":"Hallow Road","producers":["Lucan Toh","Richard Bolger","Ian Henry","Nate Bolotin","Aram Tertzakian"],"audience_score":48,"date":"2026-01-06"},
{"slug":"weapons","title":"Weapons","producers":["Zach Cregger","Roy Lee","Miri Yoon","J.D. Lifshitz","Raphael Margules"],"audience_score":85,"date":"2025-09-09"},
{"slug":"forbidden_fruits_2026","title":"Forbidden Fruits","producers":["Mason Novick","Diablo Cody","Trent Hubbard","Mary Anne Waterhouse"],"audience_score":72,"date":"2026-04-28"},
{"slug":"ready_or_not_2019","title":"Ready or Not","producers":["Tripp Vinson","James Vanderbilt","William Sherak","Bradley J. Fischer"],"audience_score":78,"date":"2019-08-27"},
{"slug":"dracula_2025_2","title":"Dracula","producers":["Luc Besson"],"audience_score":82,"date":"2026-03-10"},
{"slug":"the_long_walk_2025","title":"The Long Walk","producers":["Roy Lee","Steven Schneider","Francis Lawrence","Cameron MacConomy"],"audience_score":85,"date":"2025-10-21"},
{"slug":"cold_storage_2026","title":"Cold Storage","producers":["Gavin Polone","David Koepp"],"audience_score":75,"date":"2026-03-06"},
{"slug":"scream_7","title":"Scream 7","producers":["William Sherak","James Vanderbilt","Paul Neinstein"],"audience_score":73,"date":"2026-03-31"},
{"slug":"whistle_2025","title":"Whistle","producers":["Whitney Brown","David Gross","Macdara Kelleher"],"audience_score":55,"date":"2026-03-03"},
{"slug":"companion_2025","title":"Companion","producers":["Zach Cregger","Roy Lee","J.D. Lifshitz","Josh Mack","Raphael Margules"],"audience_score":88,"date":"2025-02-18"},
{"slug":"the_bride_2026","title":"THE BRIDE!","producers":["Maggie Gyllenhaal","Emma Tillinger Koskoff","Talia Kleinhendler","Osnat Handelsman-Keren"],"audience_score":69,"date":"2026-04-07"},
{"slug":"return_to_silent_hill","title":"Return to Silent Hill","producers":["Victor Hadida","Molly Hassell"],"audience_score":28,"date":"2026-02-24"},
{"slug":"the_life_of_chuck","title":"The Life of Chuck","producers":["Trevor Macy","Mike Flanagan"],"audience_score":88,"date":"2025-07-29"},
{"slug":"predator_badlands","title":"Predator: Badlands","producers":["John Davis","Brent O'Connor","Marc Toberoff","Dan Trachtenberg","Ben Rosenblatt"],"audience_score":94,"date":"2026-01-06"},
{"slug":"star_wars_the_last_jedi","title":"Star Wars: The Last Jedi","producers":["Kathleen Kennedy","Ram Bergman"],"audience_score":41,"date":"2018-03-11"},
{"slug":"frankenstein_2025","title":"Frankenstein","producers":["Guillermo del Toro","J. Miles Dale"],"audience_score":94,"date":"2025-11-07"},
{"slug":"the_martian","title":"The Martian","producers":["Simon Kinberg","Michael Schaefer","Aditya Sood","Mark Huffam"],"audience_score":91,"date":"2015-12-22"},
{"slug":"together_2025","title":"Together","producers":["Mike Cowap","Andrew Mittman","Erik Feig","Julia Hammer","Tim Headington","Max Silva","Alison Brie","Dave Franco"],"audience_score":75,"date":"2025-08-26"},
{"slug":"the_hunger_games_the_ballad_of_songbirds_and_snakes","title":"The Hunger Games: The Ballad of Songbirds & Snakes","producers":["Nina Jacobson","Brad Simpson","Francis Lawrence"],"audience_score":89,"date":"2023-12-19"},
{"slug":"star_wars_the_rise_of_skywalker","title":"Star Wars: The Rise of Skywalker","producers":["Kathleen Kennedy","J.J. Abrams","Michelle Rejwan"],"audience_score":86,"date":"2019-12-20"},
{"slug":"jurassic_world_rebirth","title":"Jurassic World Rebirth","producers":["Frank Marshall","Patrick Crowley"],"audience_score":70,"date":"2025-08-05"},
{"slug":"1071806-independence_day","title":"Independence Day","producers":["Dean Devlin"],"audience_score":75,"date":"2012-09-18"},
{"slug":"touch_me_2025","title":"Touch Me","producers":["Addison Heimann","John Humber","David Lawson Jr."],"audience_score":null,"date":"2026-04-07"},
{"slug":"godzilla_x_kong_the_new_empire","title":"Godzilla x Kong: The New Empire","producers":["Mary Parent","Alex Garcia","Eric McLeod","Thomas Tull","Brian Rogers"],"audience_score":89,"date":"2024-05-14"},
{"slug":"star_wars_episode_iii_revenge_of_the_sith","title":"Star Wars: Episode III - Revenge of the Sith","producers":["Rick McCallum"],"audience_score":66,"date":"2015-04-10"},
{"slug":"hamlet_2025","title":"Hamlet","producers":["James Wilson","Riz Ahmed","Michael Lesslie","Allie Moore","Tommy Oliver"],"audience_score":54,"date":"2026-05-12"},
{"slug":"pillion","title":"Pillion","producers":["Lee Groombridge","Ed Guiney","Andrew Lowe","Emma Norton"],"audience_score":89,"date":"2026-03-31"},
{"slug":"1054125-shadow","title":"The Shadow","producers":["Martin Bregman","Willi Bär","Michael Scott Bregman"],"audience_score":45,"date":"2015-09-10"},
{"slug":"1068832-sense_and_sensibility","title":"Sense and Sensibility","producers":["Lindsay Doran"],"audience_score":90,"date":"2012-04-16"},
{"slug":"50_first_dates","title":"50 First Dates","producers":["Jack Giarraputo","Michael Ewing","Steve Golin"],"audience_score":65,"date":"2013-03-26"},
{"slug":"9_to_5","title":"9 to 5","producers":["Bruce Gilbert"],"audience_score":74,"date":"2015-11-25"},
{"slug":"above_and_below_2026","title":"Above and Below","producers":["Frank Ariza","David Hillary","Mark Boot","Jamie R. Thompson","Carmen Aguado","Manu Vega"],"audience_score":null,"date":"2026-08-25"},
{"slug":"alien_covenant","title":"Alien: Covenant","producers":["Ridley Scott","Mark Huffam","Michael Schaefer","David Giler","Walter Hill"],"audience_score":55,"date":"2017-07-10"},
{"slug":"american_doctor","title":"American Doctor","producers":["Poh Si Teng","Kirstine Barfod","Reem Haddad"],"audience_score":96,"date":null},
{"slug":"american_psycho","title":"American Psycho","producers":["Christian Halsey Solomon","Chris Hanley","Edward R. Pressman"],"audience_score":85,"date":"2015-01-13"},
{"slug":"annie_2012","title":"Annie","producers":["Jada Pinkett Smith","Will Smith","Caleeb Pinkett","Jay-Z","Laurence \"Jay\" Brown","Tyran Smith"],"audience_score":59,"date":"2015-12-10"},
{"slug":"any_given_sunday","title":"Any Given Sunday","producers":["Dan Halsted","Lauren Shuler Donner","Clayton Townsend"],"audience_score":73,"date":"2010-09-27"},
{"slug":"atlas_king","title":"Atlas King","producers":["Nika Agiashvili","Michael Bisping","George Finn","Savannah Belcher","Mike Campbell","Ben Holland","Deanna Plascencia","Zaina Tibi"],"audience_score":null,"date":null},
{"slug":"avatar_aang_the_last_airbender","title":"Avatar Aang: The Last Airbender","producers":["Latifa Ouaou","Maryann Garger","Alex Loots","Dagan Potter","Bryan Konietzko","Michael Dante DiMartino"],"audience_score":99,"date":"2026-07-25"},
{"slug":"backrooms","title":"Backrooms","producers":["James Wan","Michael Clear","Roberto Patino","Shawn Levy","Dan Cohen","Dan Levine","Oz Perkins","Chris Ferguson","Peter Chernin","Jenno Topping","Kori Adelson"],"audience_score":74,"date":"2026-07-14"},
{"slug":"barbara_forever","title":"Barbara Forever","producers":["Claire Edelman","Brydie O'Connor","Elijah Stevens"],"audience_score":null,"date":null},
{"slug":"best_little_whorehouse_in_texas","title":"The Best Little Whorehouse in Texas","producers":["Thomas L. Miller","Edward K. Milkis","Robert L. Boyett"],"audience_score":69,"date":"2015-05-08"},
{"slug":"blue_film","title":"Blue Film","producers":["Adam Kersh","Will Youmans","Bijan Kazerooni","Waylon Sall"],"audience_score":67,"date":"2026-06-12"},
{"slug":"boorman_and_the_devil","title":"Boorman and the Devil","producers":["Jim Fall","David Kittredge","Travis Stevens"],"audience_score":null,"date":null},
{"slug":"borderlands","title":"Borderlands","producers":["Ari Arad","Avi Arad","Erik Feig"],"audience_score":48,"date":"2024-08-30"},
{"slug":"buddy_2026","title":"Buddy","producers":["Tyler Davidson","Drew Sykes","Raphael Margules","J.D. Lifshitz","Tracy Rosenblum"],"audience_score":76,"date":null},
{"slug":"by_any_means_2026","title":"By Any Means","producers":["Alex Lebovici","Chester Algernal Gordon","Elegance Bratton","Basil Iwanyk","Erica Lee","Mark Wahlberg","Stephen Levinson"],"audience_score":88,"date":null},
{"slug":"cars","title":"Cars","producers":["Darla K. Anderson"],"audience_score":80,"date":"2014-01-01"},
{"slug":"cocoon_one_summer_of_girlhood","title":"Cocoon: One Summer of Girlhood","producers":["Hitomi Tateno"],"audience_score":null,"date":null},
{"slug":"colony","title":"Colony","producers":["Hailey Yoomin Yang","Sung Joon-ho"],"audience_score":94,"date":null},
{"slug":"coyote_vs_acme","title":"Coyote vs. Acme","producers":["Christopher DeFaria","James Gunn"],"audience_score":94,"date":null},
{"slug":"david_2025","title":"David","producers":["Tim Keller","Rita Mbanga","Steve Pegram"],"audience_score":98,"date":"2026-01-27"},
{"slug":"dear_you","title":"Dear You","producers":[],"audience_score":95,"date":null},
{"slug":"den_of_thieves","title":"Den of Thieves","producers":["Mark Canton","Tucker Tooley","Gerard Butler","Alan Siegel"],"audience_score":64,"date":"2018-03-25"},
{"slug":"digger_2026","title":"Digger","producers":["Alejandro González Iñárritu","Mary Parent","Tom Cruise","Michael Sharp"],"audience_score":null,"date":null},
{"slug":"dire_duplicity","title":"Dire Duplicity","producers":[],"audience_score":null,"date":null},
{"slug":"disclosure_day","title":"Disclosure Day","producers":["Kristie Macosko Krieger","Steven Spielberg"],"audience_score":69,"date":"2026-07-21"},
{"slug":"dont_say_good_luck","title":"Don't Say Good Luck","producers":["Adam Sandler","Jackie Sandler","Jordan Horowitz","Brian Kavanaugh-Jones","Fred Berger"],"audience_score":80,"date":"2026-08-14"},
{"slug":"drawn_together","title":"Drawn Together","producers":["Carolina Bang","Alex de la Iglesia"],"audience_score":null,"date":"2026-09-09"},
{"slug":"drive-angry","title":"Drive Angry","producers":["Michael De Luca","René Besson","Adam Fields"],"audience_score":37,"date":"2011-05-31"},
{"slug":"evil_dead_burn","title":"Evil Dead Burn","producers":["Rob Tapert","Sam Raimi"],"audience_score":74,"date":"2026-08-04"},
{"slug":"fall_2_deadpoint","title":"Fall 2: Deadpoint","producers":["James Harris","Mark Lane","Scott Mann","David Haring","Christian Mercuri"],"audience_score":61,"date":null},
{"slug":"filipinana_2026","title":"Filipiñana","producers":["Jeremy Chua","Alex Polunin","Bianca Balbuena","Bradley Liew","Nadia Turincev","Omar El Kadi","Rafael Manuel"],"audience_score":null,"date":null},
{"slug":"finding_emily","title":"Finding Emily","producers":["Tim Bevan","Eric Fellner","Olivier Kaempfer"],"audience_score":89,"date":null},
{"slug":"five_nights_at_freddys","title":"Five Nights at Freddy's","producers":["Jason Blum","Scott Cawthon"],"audience_score":85,"date":"2023-10-27"},
{"slug":"forgotten_island","title":"Forgotten Island","producers":["Mark Swift"],"audience_score":null,"date":null},
{"slug":"franz","title":"Franz","producers":["Sarka Cimbalova","Agnieszka Holland"],"audience_score":null,"date":null},
{"slug":"goldeneye","title":"GoldenEye","producers":["Barbara Broccoli","Michael G. Wilson","Albert R. Broccoli"],"audience_score":83,"date":"2016-10-01"},
{"slug":"hacksaw_ridge","title":"Hacksaw Ridge","producers":["Bill Mechanic","David Permut","Terry Benedict","Paul Currie","Bruce Davey","William D. Johnson","Tyler Thompson","Brian Oliver"],"audience_score":92,"date":"2017-02-07"},
{"slug":"hadestown_the_musical","title":"Hadestown: The Musical","producers":["Hunter Arnold","Tom Kirdahy","Mara Isaacs","Dale Franzen"],"audience_score":98,"date":"2026-08-25"},
{"slug":"heart_of_the_beast","title":"Heart of the Beast","producers":["Damien Chazelle","Olivia Hamilton","David Ayer","Brad Pitt","Marty Bowen"],"audience_score":null,"date":null},
{"slug":"home_alone_2_lost_in_new_york","title":"Home Alone 2: Lost in New York","producers":["John Hughes"],"audience_score":63,"date":"2013-03-01"},
{"slug":"hope_2026","title":"Hope","producers":["Kim Saemi","Son Seung-hyeon"],"audience_score":null,"date":null},
{"slug":"house_of_worship","title":"House of Worship","producers":["Paul Mabury","John Hartley"],"audience_score":null,"date":"2026-09-01"},
{"slug":"how_to_rob_a_bank_2026","title":"How to Rob a Bank","producers":["Jeb Brody","Brian Grazer","Jeb Brody","Allan Mandelbaum","Kelly McCormick","David Leitch"],"audience_score":null,"date":null},
{"slug":"i_want_your_sex","title":"I Want Your Sex","producers":["Gregg Araki","Seth Caplan","Teddy Schwarzman","Michael Heimler","Courtney Cunniff","Karley Sciortino"],"audience_score":65,"date":"2026-09-01"},
{"slug":"idiots_2026","title":"Idiots","producers":["Alex Orr","Brandon James","Dave Franco","Ford Corbett","Nathan Klingher"],"audience_score":60,"date":null},
{"slug":"if_i_go_will_they_miss_me","title":"If I Go Will They Miss Me","producers":["Josh Peters","Saba Zerehi","Ben Stillman"],"audience_score":null,"date":null},
{"slug":"insidious_out_of_the_further","title":"Insidious: Out of the Further","producers":["Jason Blum","Oren Peli","James Wan","Leigh Whannell"],"audience_score":69,"date":null},
{"slug":"jackass_best_and_last","title":"Jackass: Best and Last","producers":["Jeff Tremaine","Spike Jonze","Johnny Knoxville"],"audience_score":82,"date":"2026-08-11"},
{"slug":"kpop_demon_hunters","title":"KPop Demon Hunters","producers":["Michelle L.M. Wong"],"audience_score":99,"date":"2025-06-20"},
{"slug":"lesbian_space_princess","title":"Lesbian Space Princess","producers":["Tom Phillips"],"audience_score":33,"date":"2025-11-18"},
{"slug":"mayday_2026","title":"Mayday","producers":["David Ellison","Dana Goldberg","Don Granger","Ashley Fox","Johnny Pariseau","Jonathan M. Goldstein","John Francis Daley"],"audience_score":67,"date":"2026-09-04"},
{"slug":"michael","title":"Michael","producers":["Graham King","John Branca","John McClain"],"audience_score":97,"date":"2026-06-09"},
{"slug":"minions_and_monsters","title":"Minions & Monsters","producers":["Christopher Meledandri","Bill Ryan"],"audience_score":75,"date":"2026-08-11"},
{"slug":"motor_city","title":"Motor City","producers":["Jon Berg","Cliff Roberts","Greg Silverman","Joshua Harris"],"audience_score":65,"date":"2026-08-25"},
{"slug":"muppet_treasure_island","title":"Muppet Treasure Island","producers":["Brian Henson","Martin G. Baker"],"audience_score":77,"date":"2014-01-01"},
{"slug":"mutiny_2026","title":"Mutiny","producers":["Marc Butan","Jason Statham"],"audience_score":86,"date":"2026-09-08"},
{"slug":"my_neighbor_totoro","title":"My Neighbor Totoro","producers":["Toru Hara","Ned Lott"],"audience_score":98,"date":"2019-12-10"},
{"slug":"ne_zha_ii","title":"Ne Zha II","producers":["Wenzhang Liu"],"audience_score":98,"date":"2025-09-16"},
{"slug":"never_been_kissed","title":"Never Been Kissed","producers":["Sandy Isaac","Nancy Juvonen"],"audience_score":69,"date":"2013-08-23"},
{"slug":"oasis_dont_look_back_in_anger","title":"Oasis: Don't Look Back in Anger","producers":["Steven Knight","Guy Heeley","Davud Karbassioun"],"audience_score":null,"date":null},
{"slug":"onslaught","title":"Onslaught","producers":["Simon Barrett","Andrew Swett","Alexander Black","Jeremy Platt"],"audience_score":62,"date":null},
{"slug":"other_mommy","title":"Other Mommy","producers":["James Wan"],"audience_score":null,"date":null},
{"slug":"passion_of_the_christ","title":"The Passion of the Christ","producers":["Bruce Davey","Mel Gibson","Stephen McEveety"],"audience_score":81,"date":"2015-11-25"},
{"slug":"paw_patrol_the_dino_movie","title":"PAW Patrol: The Dino Movie","producers":["Jennifer Dodge","Laura Clunie","Toni Stevens"],"audience_score":95,"date":null},
{"slug":"practical_magic_2","title":"Practical Magic 2","producers":["Denise Di Novi","Sandra Bullock","Nicole Kidman"],"audience_score":null,"date":null},
{"slug":"predator_killer_of_killers","title":"Predator: Killer of Killers","producers":["John Davis","Dan Trachtenberg","Marc Toberoff","Ben Rosenblatt"],"audience_score":88,"date":"2025-06-06"},
{"slug":"primetime","title":"Primetime","producers":["Robert Pattinson","Brighton McCloskey","Lars Knudsen","Ari Aster","Brian Kavanaugh-Jones","Fred Berger","William Iannaccone"],"audience_score":null,"date":null},
{"slug":"renfield","title":"Renfield","producers":["Robert Kirkman","David Alpert","Bryan Furst","Sean Furst","Chris McKay"],"audience_score":78,"date":"2023-05-02"},
{"slug":"resident_evil_2026","title":"Resident Evil","producers":["Robert Kulzer","Roy Lee","Miri Yoon","Carter Swan","Asad Qizilbash"],"audience_score":null,"date":null},
{"slug":"resident_evil_the_final_chapter","title":"Resident Evil: The Final Chapter","producers":["Jeremy Bolt","Robert Kulzer","Samuel Hadida"],"audience_score":47,"date":"2017-05-03"},
{"slug":"rocky_horror_picture_show","title":"The Rocky Horror Picture Show","producers":["Michael White"],"audience_score":85,"date":"2015-11-25"},
{"slug":"runner_2026","title":"Runner","producers":["Mark Fasano","Todd Garner","Deborah Glover","Jeffrey Greenstein","Alan Ritchson"],"audience_score":null,"date":null},
{"slug":"scary_movie_2026","title":"Scary Movie","producers":["Rick Alvarez","Craig Wayans","Marlon Wayans","Shawn Wayans","Keenen Ivory Wayans"],"audience_score":64,"date":"2026-07-21"},
{"slug":"shaun_the_sheep_the_beast_of_mossy_bottom","title":"Shaun the Sheep: The Beast of Mossy Bottom","producers":["Richard Beek"],"audience_score":null,"date":null},
{"slug":"signs","title":"Signs","producers":["M. Night Shyamalan","Frank Marshall","Sam Mercer"],"audience_score":67,"date":"2016-08-11"},
{"slug":"sixth_sense","title":"The Sixth Sense","producers":["Kathleen Kennedy","Frank Marshall","Barry Mendel"],"audience_score":90,"date":"2016-07-08"},
{"slug":"snakes_on_a_plane","title":"Snakes on a Plane","producers":["Gary Levinsohn","Craig Berenson","Don Granger","Mark Allan Staubach","Cathy Pallo"],"audience_score":49,"date":"2009-04-01"},
{"slug":"spa_weekend","title":"Spa Weekend","producers":["Teddy Schwarzman","John Friedberg","Michael Heimler","Suzanne Todd"],"audience_score":73,"date":null},
{"slug":"spider_man_brand_new_day","title":"Spider-Man: Brand New Day","producers":["Kevin Feige","Amy Pascal","Avi Arad","Rachel O'Connor"],"audience_score":97,"date":null},
{"slug":"steel_magnolias","title":"Steel Magnolias","producers":["Ray Stark"],"audience_score":89,"date":"2012-04-16"},
{"slug":"stephen_kings_it","title":"Stephen King's It","producers":[],"audience_score":64,"date":"2016-09-20"},
{"slug":"straight_talk","title":"Straight Talk","producers":["Robert Chartoff","Fred Berner"],"audience_score":59,"date":"2013-03-01"},
{"slug":"supergirl_2026","title":"Supergirl","producers":["James Gunn","Peter Safran"],"audience_score":72,"date":"2026-07-28"},
{"slug":"teenage_sex_and_death_at_camp_miasma","title":"Teenage Sex and Death at Camp Miasma","producers":["Dede Gardner","Jeremy Kleiner","Brad Pitt"],"audience_score":78,"date":null},
{"slug":"the_brink_of_war","title":"The Brink of War","producers":["John Logan Pierson","Sidney Kimmel","Matt Aragachi","Christopher Hammond","Tyler Zacharia","John Logan Pierson","Michael Russell Gunn"],"audience_score":87,"date":"2026-09-01"},
{"slug":"the_dog_stars","title":"The Dog Stars","producers":["Ridley Scott","Michael A. Pruss","Mark L. Smith","Cliff Roberts"],"audience_score":70,"date":null},
{"slug":"the_end_of_oak_street","title":"The End of Oak Street","producers":["J.J. Abrams","Hannah Minghella","Jon Cohen","David Robert Mitchell","Matt Jackson","Tommy Harper"],"audience_score":76,"date":"2026-09-28"},
{"slug":"the_girl_in_the_river","title":"The Girl in the River","producers":["Rick Moore","Joe Lemmon","Andrew Stevens"],"audience_score":null,"date":"2026-09-04"},
{"slug":"the_hunger_games","title":"The Hunger Games","producers":["Nina Jacobson","Jon Kilik"],"audience_score":81,"date":"2016-09-09"},
{"slug":"the_hunger_games_catching_fire","title":"The Hunger Games: Catching Fire","producers":["Jon Kilik","Nina Jacobson"],"audience_score":89,"date":"2016-08-26"},
{"slug":"the_invite","title":"The Invite","producers":["David Permut","Ben Browning","Megan Ellison"],"audience_score":89,"date":"2026-08-11"},
{"slug":"the_iron_claw_2023","title":"The Iron Claw","producers":["Tessa Ross","Juliette Howell","Angus Lamont","Sean Durkin","Derrin Schlesinger"],"audience_score":94,"date":"2024-02-13"},
{"slug":"the_magic_faraway_tree","title":"The Magic Faraway Tree","producers":["Pippa Harris","Nicolas Brown","Danny Perkins","Jane Hooks"],"audience_score":81,"date":null},
{"slug":"the_odyssey_2026","title":"The Odyssey","producers":["Emma Thomas","Christopher Nolan"],"audience_score":97,"date":null},
{"slug":"the_pout_pout_fish","title":"The Pout-Pout Fish","producers":[],"audience_score":74,"date":null},
{"slug":"the_runner_2026","title":"The Runner","producers":["David Kosse"],"audience_score":35,"date":"2026-09-02"},
{"slug":"the_salt_path","title":"The Salt Path","producers":["Elizabeth Karlsen","Stephen Woolley","Lloyd Levin","Beatriz Levin","Thorsten Schumacher","Norman Merry","Kristin Irving","Peter Hampden"],"audience_score":60,"date":null},
{"slug":"the_secret_woman","title":"The Secret Woman","producers":["Marcella Lindstad Dichmann"],"audience_score":null,"date":"2026-08-28"},
{"slug":"the_social_reckoning","title":"The Social Reckoning","producers":["Todd Black","Peter Rice","Aaron Sorkin","Stuart M. Besser"],"audience_score":null,"date":null},
{"slug":"the_sun_never_sets_2026","title":"The Sun Never Sets","producers":["Jake Johnson","Ashleigh Snead","Joe Swanberg","Dakota Fanning","Cory Michael Smith"],"audience_score":null,"date":null},
{"slug":"the_super_mario_bros_movie","title":"The Super Mario Bros. Movie","producers":["Christopher Meledandri","Shigeru Miyamoto"],"audience_score":95,"date":"2023-05-16"},
{"slug":"the_uprising_2026","title":"The Uprising","producers":["Jason Blum","Paul Greengrass","Gregory Goodman","Joanna Kaye","Joe Neurauter","Lars Sylvest"],"audience_score":null,"date":null},
{"slug":"the_weight_2026","title":"The Weight","producers":["Simon Fields","Nathan Fields","Ryan Hawke","Jonas Katzenstein","Maximilian Leo"],"audience_score":null,"date":null},
{"slug":"the_whisper_man","title":"The Whisper Man","producers":["Anthony Russo","Joe Russo"],"audience_score":39,"date":"2026-08-28"},
{"slug":"the_wolf_of_wall_street_2013","title":"The Wolf of Wall Street","producers":["Leonardo DiCaprio","Riza Aziz","Joey McFarland","Emma Tillinger Koskoff"],"audience_score":83,"date":"2015-12-12"},
{"slug":"the_wrong_girls","title":"The Wrong Girls","producers":[],"audience_score":68,"date":"2026-09-01"},
{"slug":"the_year_dolly_parton_was_my_mom_2011","title":"The Year Dolly Parton Was My Mom","producers":["Barbara Shrier"],"audience_score":36,"date":"2017-04-04"},
{"slug":"tom_and_jerry_forbidden_compass","title":"Tom and Jerry: Forbidden Compass","producers":[],"audience_score":null,"date":null},
{"slug":"tony_2026","title":"Tony","producers":["Tim White","Trevor White","Matthew Miller","Matt Johnson"],"audience_score":92,"date":null},
{"slug":"toy_story_5","title":"Toy Story 5","producers":["Lindsey Collins","Jessica Choi"],"audience_score":94,"date":"2026-08-18"},
{"slug":"transformers_the_the_movie","title":"The Transformers: The Movie","producers":["Joe Bacal","Tom Griffin","Nelson Shin"],"audience_score":88,"date":"2017-05-21"},
{"slug":"verity","title":"Verity","producers":["Nick Antosca","Alex Hedlund","Stacey Sher","Michael Showalter","Jordana Mollick","Anne Hathaway","Colleen Hoover"],"audience_score":null,"date":null},
{"slug":"virginia_woolfs_night_and_day","title":"Virginia Woolf's Night & Day","producers":["Justine Waddell","Christopher Figg","Meg Thomson","Stephen Julius","Julie Link","Philipp Steffens"],"audience_score":null,"date":null},
{"slug":"wallace_and_gromit_vengeance_most_fowl","title":"Wallace & Gromit: Vengeance Most Fowl","producers":["Richard Beek","Claire Jennings"],"audience_score":90,"date":"2025-01-03"},
{"slug":"why_did_i_get_married_again","title":"Why Did I Get Married Again?","producers":["Tyler Perry","Angi Bones","Tony Strickland"],"audience_score":null,"date":"2026-09-09"},
{"slug":"worst_witch","title":"The Worst Witch","producers":[],"audience_score":78,"date":null},
{"slug":"young_washington","title":"Young Washington","producers":["Adam Abel","Jon Erwin","Chip Diggins","Benton Crane","Edmund Sampson","Tyler Zacharia","Kristopher Kimlin"],"audience_score":92,"date":"2026-08-11"},
{"slug":"zootopia_2","title":"Zootopia 2","producers":["Yvett Merino"],"audience_score":95,"date":"2026-01-27"}
]''')


def eligible_movies(facts):
    return [movie for movie in facts if 'kevin feige' in {key(name) for name in movie['producers']}]


def winners(facts):
    eligible = eligible_movies(facts)
    numeric = [movie for movie in eligible if type(movie['audience_score']) is int
               and 0 <= movie['audience_score'] <= 100]
    require(numeric, 'no numeric audience score among eligible movies')
    maximum = max(movie['audience_score'] for movie in numeric)
    return [movie for movie in numeric if movie['audience_score'] == maximum]


def audience_value(dom, card=False):
    content = dom if card else re.split(r'\n\s*- heading .*?\[level=[23]\]', main_dom(dom), maxsplit=1)[0]
    leaves = leaf_texts(content)
    found = []
    for i, value in enumerate(leaves):
        if key(value) != 'audience score':
            continue
        # Card icons precede their value; the detail label follows its value.
        candidates = leaves[i + 1:i + 2] if card else leaves[max(0, i - 1):i]
        for candidate in candidates:
            match = re.fullmatch(r'(\d{1,3})\s*%', candidate)
            if match:
                found.append(int(match[1]))
            elif candidate in ('--', 'N/A'):
                found.append(None)
    return found[0] if len(found) == 1 else 'UNPROVEN'


def title_pattern(title):
    parts = re.split(r'\s*&\s*', title)
    return r'(?<!\w)' + r'\s*(?:&|and)\s*'.join(re.escape(part) for part in parts) + r'(?!\w)'


def score_values(text):
    text = re.sub(r'(?m)^\s*(?:[-*]|\d+[.)])\s*', '', text)
    matches = list(re.finditer(r'(?<!\d)(\d{1,3})(?:\.0)?\s*(?:%|(?:out of|/)\s*100)(?!\d)', text, re.I))
    if not matches:
        matches = list(re.finditer(r'audience\s+score\s*(?:is|of|:|=)?\s*(\d{1,3})(?!\d)', text, re.I))
    if not matches:
        without_dates = text
        for start, end, _ in reversed(dates(text)):
            without_dates = without_dates[:start] + ' ' + without_dates[end:]
        matches = [match for match in re.finditer(r'(?<![\w.])(\d{1,3})(?:\.0)?(?![\w.]|\.\d)', without_dates)
                   if int(match[1]) <= 100]
    return [int(match[1]) for match in matches]



def normalized_answer(answer):
    """Normalize displayed emphasis and JSON date slots, preserving movie pairing."""
    def date_fields(pairs):
        record = {}
        seen_date = False
        for name, value in pairs:
            field = re.sub(r'[^a-z]', '', name.casefold())
            if field in {'releasedatestreaming', 'streamingreleasedate', 'streamingdate', 'date'}:
                require(not seen_date, 'answer repeats or contradicts a streaming date field')
                seen_date = True
                name = 'release_date_streaming'
            require(name not in record, 'answer repeats a JSON field')
            record[name] = value
        return record

    text = answer.strip()
    fenced = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', text, re.I | re.S)
    if fenced:
        text = fenced[1]
    try:
        parsed = json.loads(text, object_pairs_hook=date_fields)
    except json.JSONDecodeError:
        # Only paired, single-line display markers are removed. JSON keys and
        # values take the structured path above, so underscores stay intact.
        return re.sub(r'(\*\*|__|(?<!\w)[*_]|`)(?=\S)([^\n]+?)(?<=\S)\1', r'\2', text)
    return json.dumps(parsed, ensure_ascii=False)


def missing_date_answer(text):
    """Recognize an explicit absent streaming date, never mere omitted text."""
    if (dates(text) or re.search(r"\b" + MONTH + r"\s+\d{4}\b|\b\d{4}[-/]\d{1,2}\b|\d{4}年\s*\d{1,2}月", text, re.I)):
        return False
    missing = r"(?:not\s+(?:listed|provided|shown|available)|unlisted|unavailable|n/?a|--|—|未列出|未提供|未显示|没有列出)"
    label = r"(?:release\s+date\s*\(\s*streaming\s*\)|streaming(?:\s+release)?\s+date|流媒体(?:上映|发行|发布)?日期)"
    # Reject a partial date explicitly assigned to streaming. Bare film years
    # and unrelated observations are not streaming-date assertions. This is a
    # bounded field/verb check, not a general natural-language inference step.
    streaming = r'(?:' + label + r'|\bstreams?\b|\bstreaming\b)'
    timing = r'\s*(?:[:：=—-]\s*)?(?:(?:is|was|will\s+be)\s+)?(?:(?:in|on|from|by)\s+)?'
    partial_date = r'(?:\d{4}\b|' + MONTH + r'\b)'
    if re.search(streaming + timing + partial_date, text, re.I):
        return False
    # The public task requests this field. A labelled record or a table/list
    # cell paired to the winner is an unambiguous missing-field assertion.
    if re.search(label + r"\s*(?:(?:is|was)\s+|[:：=—-]\s*)?" + missing + r"(?=$|[\s.,;。；|])", text, re.I):
        return True
    if re.search(r"no\s+" + label + r"\s+(?:is\s+|was\s+)?(?:listed|provided|shown|available)\b", text, re.I):
        return True
    if re.search(r'\bmovie\s+info\s+does\s+not\s+(?:list|show|provide)\s+(?:a\s+)?' + label, text, re.I):
        return True
    if re.search(r"\|\s*" + missing + r"\s*(?:\||$)", text, re.I | re.M):
        return True
    json_field = r'"(?:release_date_streaming|streaming_release_date|streaming_date|date|Release Date \(Streaming\))"\s*:\s*'
    return bool(re.search(json_field + r'(?:null|"' + missing + r'")(?=\s*[,}])', text, re.I))


def detail_streaming_date(dom, movie):
    if movie['date'] is None:
        return missing_streaming_date_evidence(dom, movie['title'])
    return detail_date(dom, movie['date'])


def check_answer(answer, facts=FACTS):
    require(key(answer), 'empty answer')
    answer = normalized_answer(answer)
    expected = {movie['slug']: movie for movie in winners(facts)}
    matches = []
    for movie in facts:
        for match in re.finditer(title_pattern(movie['title']), answer, re.I):
            matches.append((match.start(), match.end(), movie))
    # A short title nested inside another complete title is not another answer.
    matches = [match for match in matches if not any(other[0] <= match[0] and match[1] <= other[1]
               and (other[0], other[1]) != (match[0], match[1]) for other in matches)]
    matches.sort(key=lambda match: match[0])
    found = set()
    for index, (start, end, movie) in enumerate(matches):
        next_start = matches[index + 1][0] if index + 1 < len(matches) else len(answer)
        body = answer[end:next_start]
        if len(matches) == 1:
            body = answer
        else:
            # Tables/bullets may put score or date before their movie title.
            line_start, line_end = answer.rfind('\n', 0, start) + 1, answer.find('\n', end)
            line_end = len(answer) if line_end < 0 else line_end
            if sum(line_start <= other[0] < line_end for other in matches) == 1:
                line = answer[line_start:line_end]
                if dates(line) and score_values(line):
                    body = line
        clause_start = max(answer.rfind('\n', 0, start), answer.rfind(';', 0, start), answer.rfind('.', 0, start)) + 1
        clause_end = re.search(r'[;\n]|\.(?=\s+[A-Z]|\s*$)', answer[end:])
        context = key(answer[clause_start:end + clause_end.start()] if clause_end else answer[clause_start:next_start])
        exclusion = bool(re.search(r'\b(?:excluded|ineligible|lower|below)\b|not (?:the )?(?:highest|winner|eligible|a match)|does not qualify|不是最高|不符合|较低|排除', context))
        if movie['slug'] not in expected:
            require(exclusion, 'answer includes a movie outside the complete eligible maximum set')
            continue
        require(not exclusion, 'answer excludes a required tied maximum')
        values = [value for _, _, value in dates(body)]
        require(missing_date_answer(body) if movie['date'] is None else values == [movie['date']],
                'winner streaming date or explicit absence is missing, incorrect, duplicated or paired with another movie')
        require(score_values(body) == [movie['audience_score']], 'winner audience score is missing, incorrect or contradictory')
        found.add(movie['slug'])
    require(found == set(expected), 'answer omits one or more tied maximum movies')
    for clause in re.split(r'[;\n]', answer):
        if re.search(r'\b(?:also|another|additionally|tied with|alongside)\b', clause, re.I):
            require(any(re.search(title_pattern(movie['title']), clause, re.I) for movie in facts),
                    'answer asserts an additional unidentified movie')


def descending_dom(dom, sort_label, facts):
    main = main_dom(dom)
    if not (heading(main, 'All Movies') and re.search(r'option ["\']' + re.escape(sort_label) + r'["\'] \[selected\]', main)):
        return False
    by_slug = {movie['slug']: movie for movie in facts}
    values = []
    for slug in movie_links(dom):
        if slug not in by_slug:
            return False
        score = audience_value(movie_card(dom, slug), card=True)
        if score == 'UNPROVEN' or score != by_slug[slug]['audience_score']:
            return False
        values.append(-1 if score is None else score)
    return bool(values) and values == sorted(values, reverse=True)


def prove_producers(run, movie):
    return run.prove('Movie_Info_Producer_' + movie['slug'], {'/m/' + movie['slug']}, 0,
                     lambda dom: detail_producers(dom, movie),
                     'The Movie Info Producer field lists exactly: ' + ', '.join(movie['producers']) + '. Names under other roles do not count.')


def prove_audience(run, movie):
    path = '/m/' + movie['slug']
    expected = movie['audience_score']
    for frame in run.frames:
        if frame.path == path:
            predicate = lambda dom: audience_value(dom) == expected
            claim = 'This movie page visibly labels its Audience Score as ' + ('missing (--), not a number.' if expected is None else str(expected) + '%.')
        elif frame.path.startswith('/browse/') or frame.path in ('/', '/search') or frame.path.startswith('/celebrity/'):
            predicate = lambda dom: audience_value(movie_card(dom, movie['slug']), card=True) == expected
            claim = movie['title'] + ' has the explicitly labelled Audience score ' + ('missing (--).' if expected is None else str(expected) + '% on its own card.')
        else:
            continue
        if run.supports(frame, predicate, claim):
            run.evidence.append({'check': 'labelled_audience_' + movie['slug'], 'step': frame.position // 2, 'path': frame.path,
                                 'source': 'synchronous_dom' if frame.dom is not None else 'anchored_screenshot'})
            return frame.position
    raise VerificationError('labelled audience score not observed for ' + movie['title'])


def discovery(run, eligible):
    slugs = {movie['slug'] for movie in eligible}
    for frame in run.frames:
        if not (frame.path in ('/', '/search') or frame.path.startswith('/browse/') or frame.path.startswith('/celebrity/')):
            continue
        if run.supports(frame, lambda dom: bool(slugs.intersection(movie_links(dom))),
                        'The site browsing, search, or person-filmography UI visibly links to at least one of these candidate movies: ' + ', '.join(movie['title'] for movie in eligible) + '.'):
            run.evidence.append({'check': 'site_candidate_discovery', 'step': frame.position // 2, 'path': frame.path})
            return
    raise VerificationError('no relevant site browsing or search discovery was observed')


def eligible_comparison(run, facts):
    eligible = eligible_movies(facts)
    discovery(run, eligible)
    for movie in eligible:
        prove_producers(run, movie)
        prove_audience(run, movie)
    return 'all_eligible_comparison'


def global_descending(run, facts):
    selected = winners(facts)
    maximum = selected[0]['audience_score']
    threshold = [movie for movie in facts if type(movie['audience_score']) is int and movie['audience_score'] >= maximum]
    below = [movie for movie in facts if type(movie['audience_score']) is int and movie['audience_score'] < maximum]
    seen = set()
    boundary = not below
    accepted_frames = []
    for frame in run.frames:
        if frame.path != '/browse/movies':
            continue
        params = parse_qs(urlsplit(frame.url).query)
        sort = params.get('sort', ['popular'])[0]
        if sort not in ('audience', 'popular') or any(params.get(name, [''])[0] for name in ('genre', 'certified_fresh', 'rating', 'year', 'platform')):
            continue
        sort_label = 'Audience Score' if sort == 'audience' else 'Popular'
        valid = run.supports(frame, lambda dom: descending_dom(dom, sort_label, facts),
                             'The unfiltered All Movies catalog is visible with ' + sort_label + ' selected in Sort (this site sorts that selection by descending audience score).')
        if not valid:
            continue
        accepted_frames.append(frame)
        for movie in threshold:
            if movie['slug'] in seen:
                continue
            if run.supports(frame, lambda dom, movie=movie: audience_value(movie_card(dom, movie['slug']), card=True) == movie['audience_score'],
                            'The global catalog card for ' + movie['title'] + ' visibly shows Audience score ' + str(movie['audience_score']) + '%.'):
                seen.add(movie['slug'])
        if not boundary:
            # Any visibly lower card establishes that the entire maximum tie
            # band was traversed; no particular lower movie is prescribed.
            for movie in below:
                if run.supports(frame, lambda dom, movie=movie: audience_value(movie_card(dom, movie['slug']), card=True) == movie['audience_score'],
                                'A lower-ranked catalog card for ' + movie['title'] + ' visibly shows Audience score ' + str(movie['audience_score']) + '%, below ' + str(maximum) + '%.'):
                    boundary = True
                    break
    require(accepted_frames and seen == {movie['slug'] for movie in threshold} and boundary,
            'global descending catalog comparison does not cover every higher/tied score and the lower boundary')
    for movie in threshold:
        prove_producers(run, movie)
    run.evidence.append({'check': 'global_descending_threshold_and_exclusion', 'threshold': maximum,
                         'compared_movie_count': len(threshold), 'lower_boundary_observed': boundary})
    return 'global_descending_exclusion'


def check_ui(run, facts=FACTS):
    original = list(run.evidence)
    failures = []
    for proof in (eligible_comparison, global_descending):
        run.evidence[:] = original
        try:
            route = proof(run, facts)
            break
        except VerificationError as error:
            failures.append(str(error))
    else:
        run.evidence[:] = original
        raise VerificationError('Neither permitted comparison path is evidenced: ' + ' | '.join(failures))
    for movie in winners(facts):
        prove_audience(run, movie)
        run.prove('winner_streaming_date_' + movie['slug'], {'/m/' + movie['slug']}, 0,
                  lambda dom, movie=movie: detail_streaming_date(dom, movie),
                  ('The complete Movie Info section is visible through its ending and contains no Release Date (Streaming), or explicitly marks it as not listed. An unloaded or cropped section is insufficient.'
                   if movie['date'] is None else 'The Movie Info Release Date (Streaming) is ' + movie['date'] + '.'))
    run.evidence.append({'check': 'permitted_comparison_path', 'path': route})
    return route


def evaluate(run_dir, initial_db=None, after_db=None, no_llm=False):
    run = None
    try:
        run = Run(run_dir, CONTRACTS[TASK_ID], no_llm=no_llm)
        before_path = initial_db or (Path(run_dir) / 'before.db' if (Path(run_dir) / 'before.db').is_file() else Path(run_dir) / 'initial.db')
        before, after = Snapshot(before_path), Snapshot(after_db or Path(run_dir) / 'after.db')
        read_only(before, after)
        require({row['slug'] for row in before.rows['movies']} == {movie['slug'] for movie in FACTS}, 'catalog identities differ from frozen task facts')
        for movie in FACTS:
            require(before.one('movies', slug=movie['slug'])['title'] == movie['title'], 'source movie title mismatch')
        check_answer(run.data['final_answer'])
        check_ui(run)
        return {'task_id': TASK_ID, 'pass': True, 'reason': 'Complete eligible maximum, paired facts and a permitted UI comparison path are evidenced; business state is unchanged.', 'evidence': run.evidence}
    except (VerificationError, OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, sqlite3.Error) as error:
        return {'task_id': TASK_ID, 'pass': False, 'reason': str(error), 'evidence': run.evidence if run else []}


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_dir', required=True)
    parser.add_argument('--initial_db')
    parser.add_argument('--after_db')
    parser.add_argument('--no_llm', nargs='?', const='true', default='false', choices=('true', 'false', 'True', 'False'))
    args = parser.parse_args()
    result = evaluate(args.run_dir, args.initial_db, args.after_db, args.no_llm.lower() == 'true')
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result['pass'] else 1)


if __name__ == '__main__':
    cli()
