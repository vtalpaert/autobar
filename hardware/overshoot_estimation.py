class NaiveAnticipator:
    naive_overshoot = 8

    def __init__(goal_weight):
        self.goal_weight = goal_weight
    
    def update(self, measure):
        self.last_measure = measure

    def must_stop():
        return self.last_measure + self.naive_overshoot > self.goal_weight
