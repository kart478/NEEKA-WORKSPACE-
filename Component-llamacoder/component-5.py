# main.py
from brain import NEEKAEngine
from brain.user import UserRole
from brain.task import TaskStatus


def main():
    print("=" * 50)
    print("NEEKA WORK ENGINE")
    print("=" * 50)

    engine = NEEKAEngine()

    # 1. Create users
    alice = engine.create_user("Alice Johnson", "alice@neeka.io", UserRole.MANAGER)
    bob = engine.create_user("Bob Smith", "bob@neeka.io", UserRole.MEMBER)
    print(f"\n[+] Created users: {alice.name}, {bob.name}")

    # 2. Create project
    project = engine.create_project(
        "School Report",
        "Compile annual school performance report",
        alice.id,
    )
    print(f"[+] Created project: {project.name}")

    # 3. Add members
    engine.add_project_member(project.id, bob.id, alice.id)
    print(f"[+] Added {bob.name} to project")

    # 4. Create tasks
    task_a = engine.create_task(
        "Collect teacher reports",
        "Gather reports from all department heads",
        project.id,
        alice.id,
    )
    task_b = engine.create_task(
        "Compile report",
        "Compile all reports into final document",
        project.id,
        alice.id,
    )
    print(f"[+] Created tasks: {task_a.title}, {task_b.title}")

    # 5. Add dependency
    engine.add_task_dependency(task_b.id, task_a.id, alice.id)
    print(f"[+] Task B depends on Task A")

    # 6. Execute Task A
    engine.assign_task(task_a.id, bob.id, alice.id)
    engine.start_task(task_a.id, bob.id)
    engine.complete_task(task_a.id, bob.id)
    print(f"\n[✓] Completed: {task_a.title}")

    # 7. Execute Task B (should be READY now)
    print(f"[→] {task_b.title} status: {task_b.status.value}")
    engine.assign_task(task_b.id, bob.id, alice.id)
    engine.start_task(task_b.id, bob.id)
    engine.complete_task(task_b.id, bob.id)
    print(f"[✓] Completed: {task_b.title}")

    # 8. Display results
    print("\n" + "=" * 50)
    print(f"Project: {project.name}")
    print(f"Status: {project.status.value}")
    print("\nTasks:")
    for task in engine.get_project_tasks(project.id):
        status_icon = "✓" if task.status == TaskStatus.COMPLETED else "•"
        print(f"  [{status_icon}] {task.title}")
        print(f"      Status: {task.status.value}")

    print("\nEvents:")
    for event in engine.get_events():
        print(f"  * {event.event_type.value}")

    print(f"\nPROJECT STATUS: {project.status.value}")
    print("=" * 50)


if __name__ == "__main__":
    main()