# import custom libraries
from findus import Parameterspace, GeneticAlgorithm, Population

boundaries = [(1000, 2000), (100, 200), (10, 20)]
divisions = [3, 2, 2]

par = Parameterspace(boundaries, divisions)
print(par.get_weights())

print(par.get_bin_assignment(1000, 100, 10)) # 0
print(par.get_bin_assignment(1334, 100, 10)) # 1
print(par.get_bin_assignment(1668, 100, 10)) # 2

print(par.get_bin_assignment(1000, 150, 10)) # 3
print(par.get_bin_assignment(1334, 150, 10)) # 4
print(par.get_bin_assignment(1668, 150, 10)) # 5

print(par.get_bin_assignment(1000, 100, 15)) # 6
print(par.get_bin_assignment(1334, 100, 15)) # 7
print(par.get_bin_assignment(1668, 100, 15)) # 8

print(par.get_bin_assignment(1000, 150, 15)) # 9
print(par.get_bin_assignment(1334, 150, 15)) # 10
print(par.get_bin_assignment(1668, 150, 15)) # 11


par.add_experiment(10, 1000, 100, 10) # 0
par.add_experiment(10, 1000, 100, 10) # 0
par.add_experiment(10, 1000, 100, 10) # 0
par.add_experiment(10, 1000, 100, 10) # 0
par.add_experiment(10, 1334, 100, 10) # 1
par.add_experiment(10, 1334, 100, 10) # 1
par.add_experiment(10, 1334, 100, 10) # 1
par.add_experiment(10, 1668, 100, 10) # 2
par.add_experiment(10, 1668, 100, 10) # 2
par.add_experiment(2, 1000, 150, 10) # 3
par.add_experiment(2, 1334, 150, 10) # 4
par.add_experiment(2, 1668, 150, 10) # 5
par.add_experiment(2, 1000, 100, 15) # 6
par.add_experiment(0, 1334, 100, 15) # 7
par.add_experiment(0, 1668, 100, 15) # 8
par.add_experiment(0, 1000, 150, 15) # 9
par.add_experiment(0, 1334, 150, 15) # 10
par.add_experiment(0, 1668, 150, 15) # 11
print(par.get_weights())
print(par.get_bin_numbers_sorted_by_weights())

print(par.get_coordinates(3))
print(par.get_boundaries(1))


pop = Population(number_of_individuals=10, length_of_genom=5)
opt = GeneticAlgorithm(par, pop)
bins = opt.run(35)
print(f"[+] Best performing bins: {bins}")