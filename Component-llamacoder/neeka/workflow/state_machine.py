from dataclasses import dataclass
from typing import Hashable, FrozenSet

from neeka.brain.exceptions import InvalidTaskTransitionError


@dataclass(frozen=True)
class Transition:
    source: Hashable
    destination: Hashable
    trigger: str


@dataclass(frozen=True)
class StateMachine:
    states: FrozenSet[Hashable]
    transitions: FrozenSet[Transition]

    def can_transition(self, source: Hashable, destination: Hashable) -> bool:
        return any(
            transition.source == source and transition.destination == destination
            for transition in self.transitions
        )

    def validate(self, source: Hashable, destination: Hashable) -> Transition:
        if source == destination:
            return Transition(source, destination, "noop")
        for transition in self.transitions:
            if transition.source == source and transition.destination == destination:
                return transition
        raise InvalidTaskTransitionError(f"Cannot transition from {source} to {destination}")