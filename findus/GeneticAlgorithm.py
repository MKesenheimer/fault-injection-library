#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: info@faultyhardware.de.

"""
GeneticAlgorithm

This module includes all classes and functions that are necessary to search for optimal parameters in a multidimenstional parameter space.
"""

import random

class Parameterspace():
    def __init__(self, parameter_boundaries:list[tuple[float, float]], parameter_divisions:list[int]):
        """
        Initializes the class with the given parameter boundaries and divisions.
    
        Parameters:
            parameter_boundaries: A list of tuples representing the lower and upper bounds for each parameter.
            parameter_divisions: A list of integers representing the number of divisions for each parameter.
    
        Raises:
            Exception: If the lengths of parameter_boundaries and parameter_divisions are different.
            Exception: If any upper bound is lower than the corresponding lower bound.
        """
        # sanity checks
        if len(parameter_boundaries) != len(parameter_divisions):
            raise Exception(f"Error: parameter_boundaries and parameter_divisions have different lengths ({len(parameter_boundaries)} vs. {len(parameter_divisions)}).")
        for tup in parameter_boundaries:
            if tup[0] > tup[1]:
                raise Exception(f"Error: Upper bound {tup[1]} is lower than lower bound {tup[0]}.")
        self.parameter_boundaries = parameter_boundaries
        self.parameter_divisions = parameter_divisions
        self.cardinality = 1
        for num in self.parameter_divisions:
            self.cardinality *= num
        self.weights_per_bin = [0 for x in range(self.cardinality)]

    def get_cardinality(self):
        """
        Returns the cardinality of the set.
        """
        return self.cardinality

    def get_bin_assignment(self, *parameter:float) -> list[int]:
        """
        This function assigns a bin to each parameter based on its value.
        
        Parameters:
            *parameter: A list of float values representing the parameters to be assigned to bins.
        
        Returns:
            list: A list of integers representing the bin numbers for each parameter.
        """
        fact = 1
        bina = 0
        for i in range(len(self.parameter_divisions)):
            division =  self.parameter_divisions[i]
            # xdelta = (xmax - xmin) / xdiv
            delta = (self.parameter_boundaries[i][1] - self.parameter_boundaries[i][0]) / division
            bin_number = int((parameter[i] - self.parameter_boundaries[i][0]) / delta)
            #print(f"par = {parameter[i]}, delta = {delta}, bina = {bin_number}")
            if i > 0:
                fact *= self.parameter_divisions[i - 1]
            bina += fact * bin_number
        return bina

    def add_experiment(self, weight:int, *parameter:float):
        """
        Add experiment data to the dataset.
        This function adds an experiment to the dataset with the given weight and parameters.
        It checks if each parameter is within the specified boundaries.
        If any parameter is out of bounds, it prints an error message and returns without
        adding the experiment. Otherwise, it assigns the experiment to a bin and updates the weight for that bin.
    
        Parameters:
            weight: The weight to assign to the experiment.
            *parameter: The parameters for the experiment, must be within the specified boundaries.
    
        Returns:
            None
        """
        for i in range(len(self.parameter_divisions)):
            if parameter[i] < self.parameter_boundaries[i][0] or parameter[i] >= self.parameter_boundaries[i][1]:
                print("[-] Error: parameter out of bounds. Skipping.")
                print(f"[-] Dimension: {i}, lower = {self.parameter_boundaries[i][0]}, upper = {self.parameter_boundaries[i][1]}, parameter = {parameter[i]}")
                return
        bina = self.get_bin_assignment(*parameter)
        self.weights_per_bin[bina] += weight

    def get_weights(self) -> list[int]:
        """
        Returns the list of weights per bin.
    
        Returns:
            list: A list of weights corresponding to each bin.
        """
        return self.weights_per_bin

    def get_bin_numbers_sorted_by_weights(self) -> list[int]:
        """
        Returns a list of bin numbers sorted by their corresponding weights.
    
        Returns:
            list: A list of bin numbers sorted by increasing weights.
        """
        return sorted(range(len(self.weights_per_bin)), key=lambda i: self.weights_per_bin[i])

    def get_coordinates(self, bin_assignment:int) -> list[int]:
        """
        This function calculates the coordinates of a given bin assignment in a multi-dimensional binning system.
        
        Parameters:
            bin_assignment: The bin assignment for which to calculate the coordinates.
        
        Returns:
            list: A list of coordinates corresponding to the bin assignment.
        
        Raises:
            Exception: If the bin assignment exceeds the total number of bins.
        """
        bin_numbers = []
        reversed_parameter_divisions = list(reversed(self.parameter_divisions))
        fact = self.cardinality
        if bin_assignment > fact:
            raise Exception("Error: bin number exceeds total number of bins.")
        for div in reversed_parameter_divisions:
            c = (fact / div)
            b = int(bin_assignment / c)
            #print(f"bin_assignment = {bin_assignment}, fact = {fact}, div = {div}, (fact / div) = {c}, bin_number = {b}")
            bin_numbers.append(b)
            fact /= div
            bin_assignment -= int(b * c)
        return list(reversed(bin_numbers))

    def get_boundaries_from_coordinates(self, coordinates:list[float]) -> list[tuple[float, float]]:
        """
        This function calculates the boundaries for each parameter based on the given coordinates.
        
        Parameters:
            coordinates: A list of coordinates.
        
        Returns:
            list: A list of tuples representing the boundaries for each parameter.
        """
        boundaries = []
        for i in range(len(self.parameter_divisions)):
            division =  self.parameter_divisions[i]
            delta = (self.parameter_boundaries[i][1] - self.parameter_boundaries[i][0]) / division
            lower = self.parameter_boundaries[i][0] + delta * coordinates[i]
            upper = self.parameter_boundaries[i][0] + delta * (coordinates[i] + 1)
            tup = (lower, upper)
            boundaries.append(tup)
        return boundaries

    def get_boundaries(self, bin_assignment:int) -> list[tuple[float, float]]:
        """
        Returns the boundaries for a given bin assignment.

        Parameters:
            bin_assignment: The bin assignment for which to get the boundaries.

        Returns:
            list: A list of tuples representing the boundaries.
        """
        bin_numbers = self.get_coordinates(bin_assignment)
        return self.get_boundaries_from_coordinates(bin_numbers)

class Individual():
    """
    This class represents an individual with parameters, health, maximum age, and current age.

    Attributes:
        parameters: A list of parameters associated with the individual.
        health: The current health status of the individual.
        max_age: The maximum age that the individual can reach.
        age: The current age of the individual.
    """
    def __init__(self, parameters:list[int], max_age:int = 10):
        self.parameters = parameters
        self.health = 0
        self.max_age = max_age
        self.age = 0

    def set_genom(self, parameters: list[int]):
        """
        Set the parameters (genom) for the entity.

        Parameters:
            parameters: The parameters to set.
        """
        self.parameters = parameters
    
    def get_genom(self) -> list[int]:
        """
        Get the parameters (genom) of the entity.
        
        Returns:
            list: The parameters (genom) of the entity.
        """
        return self.parameters
    
    def set_health(self, health: int):
        """
        Set the health of the entity.
        
        Parameters:
            health: The health value to set.
        """
        self.health = health
    
    def get_health(self) -> int:
        """
        Get the health of the entity.
        
        Returns:
            int: The health of the entity.
        """
        return self.health
    
    def get_age(self) -> int:
        """
        Get the current age of the entity.
        
        Returns:
            int: The current age of the entity.
        """
        return self.age
    
    def get_max_age(self) -> int:
        """
        Get the maximum age of the entity.
        
        Returns:
            int: The maximum age of the entity.
        """
        return self.max_age
    
    def increase_age(self):
        """
        Increase the age of the entity by one.
        """
        self.age += 1

class Population():
    """
    A class to represent a population of individuals.
    """
    def __init__(self, number_of_individuals:int, length_of_genom:int):
        """
        Initializes a new population with a given number of individuals and genom length.

        Parameters:
            number_of_individuals: The number of individuals in the population.
            length_of_genom: The length of the genom for each individual.
        """
        if number_of_individuals < 10:
            raise Exception("Error: Population too small.")

        self.number_of_individuals = number_of_individuals
        self.length_of_genom = length_of_genom

        self.population = [None] * self.number_of_individuals
        for i in range(self.number_of_individuals):
            self.population[i] = self.generate_random_individual()

    def get_number_of_individuals(self) -> int:
        """
        Returns the number of individuals in the population.

        Returns:
            The number of individuals.
        """
        return self.number_of_individuals

    def get_length_of_genom(self) -> int:
        """
        Returns the length of the genom for each individual.

        Returns:
            The length of the genom.
        """
        return self.length_of_genom

    def generate_random_individual(self) -> Individual:
        """
        Generates a random individual with a genom of length 'length_of_genom'.

        Returns:
            A random individual.
        """
        genom = [0] * self.length_of_genom
        for i in range(self.length_of_genom):
            genom[i] = random.uniform(0, 1)
        return Individual(genom)

    def get_individuals(self) -> list[Individual]:
        """
        Returns a list of all individuals in the population.

        Returns:
            A list of individuals.
        """
        return self.population

    def set_individuals(self, individuals:list[Individual]):
        """
        Sets the population to the given list of individuals.
        
        Parameters:
            individuals: A list of individuals to set as the population.
        """
        self.population = individuals

    def sort_by_health(self):
        """
        Sorts the population by the health of each individual.
        """
        self.population = sorted(self.population, key=lambda ind: ind.get_health())

    def update_health(self, health_function):
        """
        Updates the health of each individual in the population using the given health function.

        Parameters:
            health_function: A function that takes a genom and returns a health value.
        """
        for ind in self.population:
            ind.set_health(health_function(ind.get_genom()))
            #print(ind.get_health())

    def breed(self, i:int, j:int) -> Individual:
        """
        Breeds two individuals and returns a new individual with a genom that is a combination of the two parents.

        Parameters:
            i: The index of the first parent individual.
            j: The index of the second parent individual.

        Returns:
            A new individual that is a result of breeding the two parents.
        """
        geni = self.population[i].get_genom().copy()
        genj = self.population[j].get_genom().copy()
        for k in range(len(geni)):
            select = random.randint(0, 1)
            if select == 1:
                geni[k] = genj[k]
        return Individual(geni)

    def mutate(self, i:int) -> Individual:
        """
        Mutates the genom of the individual at the given index.

        Parameters:
            i: The index of the individual to mutate.
        
        Returns:
            The mutated individual.
        """
        gene = random.randint(0, self.length_of_genom - 1)
        self.population[i].get_genom()[gene] = random.uniform(0, 1)

    def replace(self, i:int, individual:Individual):
        """
        Replaces the individual at the given index with the given individual.

        Parameters:
            i: The index of the individual to replace.
            individual: The individual to replace the old individual with.
        """
        self.population[i] = individual

    def replace_with_random(self, i:int):
        """
        Replaces the individual at the given index with a random individual.

        Parameters:
            i: The index of the individual to replace.
        """
        self.population[i] = self.generate_random_individual()

    def kill_and_replace(self):
        """
        Removes individuals from the population that have exceeded their maximum age and replaces them with random individuals.
        """
        for i in range(len(self.population)):
            if self.population[i].get_age() > self.population[i].get_max_age():
                self.population[i] = self.generate_random_individual()

    def increase_age_of_population(self):
        """
        Increases the age of each individual in the population.
        """
        for i in range(len(self.population)):
            self.population[i].increase_age()

class GeneticAlgorithm:
    """
    Class representing a Genetic Algorithm for optimizing a given problem.
    """
    def __init__(self, parameterspace:Parameterspace, population:Population, health_malus_factor:float = 1):
        """
        Initializes the Genetic Algorithm with a parameterspace, population, and an optional health malus factor.
        
        Parameters:
            parameterspace: The space of parameters over which the algorithm operates.
            population: The initial population of candidate solutions.
            health_malus_factor: A factor that penalizes solutions based on their healthiness.
        """
        self.parameterspace = parameterspace
        self.population = population
        self.health_malus_factor = health_malus_factor

    def get_bins_from_genom(self, parameters:list[int]) -> list[int]:
        """
        Converts a list of parameters into a list of bins based on the parameterspace.
        
        Parameters:
            parameters: A list of parameters.

        Returns:
            A list of bins corresponding to the parameters.
        """
        bins = [int(x * self.parameterspace.get_cardinality()) for x in parameters]
        return bins

    def health_function(self, parameters:list[int]) -> int:
        """
        Calculates the health of an individual:

            health = Sum(weight_i) - factor * malus * Sum(weight_i)
            health = (1 - factor * malus) * Sum(weight_i)

        Parameters:
            parameters: The parameters to set.
        """
        bins = self.get_bins_from_genom(parameters)
        # sum up the weights in each bin
        health = 0
        weights = self.parameterspace.get_weights()
        for b in bins:
            health += weights[b]

        # for every bin that occurs more than once, reduce health
        # (forces the algorithm to look into separate bins)
        # malus can maximal be the number of genoms (=bins),
        # therefore it is reasonable to choose health_malus_factor < (1 / number_of_bins)
        counts = {}
        for item in bins:
            counts[item] = counts.get(item, 0) + 1
        malus = 0
        for c in counts:
            if counts[c] > 1:
                malus += counts[c] - 1
        health -= (self.health_malus_factor * malus * health)

        return health

    def get_max_health(self) -> int:
        """
        Calculate the maximum health possible for an individual based on the population's genom length and the weights in the parameter space.
    
        Returns:
            Maximum health value.
        """
        genom_length = self.population.get_length_of_genom()
        return max(self.parameterspace.get_weights()) * genom_length

    def step(self) -> list[Individual]:
        """
        Perform one step of the simulation by updating the population, performing breeding, mutation, replacing weak individuals, and killing old individuals.
    
        Returns:
            List of updated individuals in the population.
        """
        self.population.increase_age_of_population()
        self.population.update_health(self.health_function)
        self.population.sort_by_health()

        # Step 1: breeding
        number_of_individuals = self.population.get_number_of_individuals()
        child12 = self.population.breed(number_of_individuals - 1, number_of_individuals - 2)
        child21 = self.population.breed(number_of_individuals - 2, number_of_individuals - 1)
        child34 = self.population.breed(number_of_individuals - 3, number_of_individuals - 4)
        child43 = self.population.breed(number_of_individuals - 4, number_of_individuals - 3)
        # replace the individuals with bad health
        self.population.replace(0, child12)
        self.population.replace(1, child21)
        self.population.replace(2, child34)
        self.population.replace(3, child43)

        # Step 2: mutate
        self.population.mutate(0)
        self.population.mutate(2)

        # Step 3: replace weak individuals with random ones
        self.population.replace_with_random(4)
        self.population.replace_with_random(5)

        # Step 4: Kill old individuals
        self.population.kill_and_replace()

        self.population.update_health(self.health_function)
        self.population.sort_by_health()

        return self.population.get_individuals()

    def run(self, threshold:float) -> list[int]:
        """
        Runs the simulation until an individual's health meets or exceeds a certain threshold.
            
        Parameters:
            threshold: The threshold as a fraction of the maximum health value.
            
        Returns:
            A list of bins derived from the genom of the individual with the highest health.
        """
        maxhealth = self.get_max_health()
        while True:
            individuals = self.step()
            for ind in individuals:
                print(f"health of ind {ind}: {ind.get_health()}")
            print()
            if individuals[0].get_health() >= maxhealth * threshold:
                parameters = individuals[0].get_genom()
                return self.get_bins_from_genom(parameters)

    def get_population(self) -> Population:
        """
        Returns the population.
        
        Returns:
            Population
        """
        return self.population

    def get_parameterspace(self) -> Parameterspace:
        """
        Returns the parameterspace.
        
        Returns:
            Parameterspace
        """
        return self.parameterspace

class OptimizationController():
    """
    Wrapper class for initializing parameter space binning and using the genetic algorithm to search for optimal paramters.

    Methods:
        __init__: Constructor of the OptimizationController. Parameter boundaries and parameter divisions must be provided. Parameters for the genetic algorithm are optional.
        print_best_performing_bins: Output the best performing parameter space bins. In these bins a successful glitch is assumed.
        step: Perform the next step of the genetic algorithm; should be called before every experiment.
        add_experiment: Add the parameters and the outcome (weights) to the parameter space.
    """

    def __init__(self, parameter_boundaries:list[tuple[int, int]], parameter_divisions:list[int], number_of_individuals:int = 10, length_of_genom:int = 20, malus_factor_for_equal_bins:float = 1):
        """
        Constructor of the OptimizationController. Parameter boundaries and parameter divisions must be provided. Parameters for the genetic algorithm are optional.

        Parameters:
            parameter_boundaries: Boundaries of all parameters to look into, for example `[(s_delay, e_delay), (s_t1, e_t1), (s_length, e_length)]`.
            parameter_divisions: Number of how many bins the individual parameter ranges should be divided into, for example `[10, 10, 5]`. Bigger values mean division into smaller bins which increases accuracy at the expense of performance (longer glitching campaign duration).
            number_of_individuals: Number of individuals used simultaneously in the genetic algorithm. Increasing this number improves accuracy at the expense of performance (longer glitching campaign duration).
            length_of_genom: Number of bins to track per individual. The larger the parameter space, the higher this number should be.
            malus_factor_for_equal_bins: Can be used to punish individuals that look into the same bin multiple times. Must be in range [0, 1]. A bigger value means a greater penalty.
        """
        self.par = Parameterspace(parameter_boundaries, parameter_divisions)
        self.pop = Population(number_of_individuals, length_of_genom)
        # renorm the malus factor to the maximum number of genoms,
        # thus malus_factor_for_equal_bins can be chosen between 0 and 1.
        if malus_factor_for_equal_bins > 1 or malus_factor_for_equal_bins < 0:
            print("[-] Error: malus_factor_for_equal_bins must be in range [0, 1].")
            sys.exit(-1)
        factor = malus_factor_for_equal_bins / length_of_genom
        self.opt = GeneticAlgorithm(self.par, self.pop, factor)
        self.i_current_individual = 0
        self.i_current_bin = 0
        self.number_of_individuals = self.pop.get_number_of_individuals()
        self.length_of_genom = self.pop.get_length_of_genom()

    def print_best_performing_bins(self):
        """
        Method that prints an overview of the best performing bins of the parameterspace. Can be called from time to time to obtain an overview of the optimization process.
        """
        number_of_individuals = self.pop.get_number_of_individuals()
        ind0 = self.pop.get_individuals()[number_of_individuals - 1]
        print(f"[+] Individual health = {ind0.get_health()}, age = {ind0.get_age()}")
        print("[+] Best performing bins:")
        genom = ind0.get_genom()
        bins = self.opt.get_bins_from_genom(genom)
        boundaries = []
        for i in range(len(bins)):
            boundary = self.par.get_boundaries(bins[i])
            print(f"    bin = {bins[i]}: {boundary}")
            boundaries.append(boundary)

    def step(self) -> list[int]:
        """
        Perform the next step in the optimization process. Should be called before the next experiment.

        Returns:
            A list of the parameters for the next experiment.
        """
        individuals = self.pop.get_individuals()
        parameters = individuals[self.i_current_individual].get_genom()
        bins = self.opt.get_bins_from_genom(parameters)
        boundaries = self.par.get_boundaries(bins[self.i_current_bin])

        random_numbers = []
        for b in boundaries:
            random_numbers.append(random.uniform(b[0], b[1]))

        # next bin
        self.i_current_bin += 1
        if self.i_current_bin >= self.length_of_genom:
            self.i_current_bin = 0
            # next individual
            self.i_current_individual += 1
            if self.i_current_individual >= self.number_of_individuals:
                self.i_current_individual = 0
                # next age step
                self.pop.set_individuals(self.opt.step())

        return [round(x, 1) for x in random_numbers]

    def add_experiment(self, weight:int, *parameter:int):
        """
        Method to add the parameters and the outcome (weights) to the parameter space. Can be used similarly to the method `Database.insert()`.

        Parameters:
            weight: Weight of the outcome of the experiment. Higher values mean a better performing bin and a better health of the individuals that track that bin.
            parameter: list of parameters that were used for the experiment.
        """
        self.par.add_experiment(weight, *parameter)
