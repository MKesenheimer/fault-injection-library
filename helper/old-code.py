# delete old experiments
experiment_id = self.database.get_latest_experiment_id()
print(experiment_id)
for i in range(0, 806):
    eid = self.database.get_latest_experiment_id()
    print(eid)
    self.database.remove(eid)