from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)


ATTACK_TYPES = [
    "normal",
    "brute_force",
    "credential_stuffing",
    "impossible_travel",
    "device_spoofing",
    "lateral_movement",
    "low_slow_exfiltration",
    "insider_drift",
]

LOCATIONS = [
    "Bengaluru",
    "Hyderabad",
    "Mumbai",
    "Delhi",
    "Pune",
    "Chennai",
    "Singapore",
    "London",
    "New York",
    "Frankfurt",
]

RESOURCES = [
    "email",
    "github",
    "jira",
    "dev_server",
    "database",
    "hr_portal",
    "finance_portal",
    "file_server",
    "admin_console",
    "credential_store",
]

COMMANDS = [
    "login",
    "read",
    "write",
    "download",
    "upload",
    "query",
    "execute",
    "enumerate",
    "privileged_command",
]

ROLES = {
    "developer": {
        "resources": ["github", "jira", "dev_server", "database", "email"],
        "commands": ["login", "read", "write", "query", "execute"],
    },
    "analyst": {
        "resources": ["email", "jira", "database", "file_server"],
        "commands": ["login", "read", "query", "download"],
    },
    "finance": {
        "resources": ["email", "finance_portal", "file_server"],
        "commands": ["login", "read", "write", "download", "upload"],
    },
    "hr": {
        "resources": ["email", "hr_portal", "file_server"],
        "commands": ["login", "read", "write", "download"],
    },
    "admin": {
        "resources": [
            "email",
            "admin_console",
            "database",
            "file_server",
            "dev_server",
        ],
        "commands": [
            "login",
            "read",
            "write",
            "query",
            "execute",
            "privileged_command",
        ],
    },
}


@dataclass
class UserProfile:
    user_id: str
    role: str
    home_location: str
    normal_start_hour: float
    normal_session_hours: float
    primary_device: str
    secondary_device: str
    typical_data_mb: float


class SecurityLogGenerator:
    def __init__(
        self,
        num_users: int = 80,
        num_days: int = 45,
        start_date: datetime | None = None,
    ):
        self.num_users = num_users
        self.num_days = num_days

        self.start_date = start_date or (
            datetime.now().replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            - timedelta(days=num_days)
        )

        self.users = self._create_users()
        self.events: list[dict] = []

    def _create_users(self) -> list[UserProfile]:
        users = []

        role_names = list(ROLES.keys())
        home_locations = LOCATIONS[:6]

        for i in range(self.num_users):
            role = random.choices(
                role_names,
                weights=[40, 20, 15, 15, 10],
                k=1,
            )[0]

            user = UserProfile(
                user_id=f"user_{i + 1:03d}",
                role=role,
                home_location=random.choice(home_locations),
                normal_start_hour=float(np.clip(np.random.normal(9.2, 0.8), 6.5, 12.0)),
                normal_session_hours=float(
                    np.clip(np.random.normal(7.5, 1.0), 4.0, 10.0)
                ),
                primary_device=f"device_{uuid.uuid4().hex[:8]}",
                secondary_device=f"device_{uuid.uuid4().hex[:8]}",
                typical_data_mb=float(np.clip(np.random.lognormal(2.2, 0.6), 2, 100)),
            )

            users.append(user)

        return users

    @staticmethod
    def _hour_to_time(day: datetime, hour: float) -> datetime:
        hour = max(0.0, min(hour, 23.95))

        whole_hour = int(hour)
        minute = int((hour - whole_hour) * 60)

        return day.replace(
            hour=whole_hour,
            minute=minute,
            second=random.randint(0, 59),
        )

    @staticmethod
    def _ip_address() -> str:
        return fake.ipv4_public()

    def _append_event(
        self,
        user: UserProfile,
        timestamp: datetime,
        session_id: str,
        resource: str,
        command: str,
        location: str,
        device_id: str,
        success: bool = True,
        data_mb: float = 0.0,
        privileged: bool = False,
        attack_type: str = "normal",
    ) -> None:
        self.events.append(
            {
                "event_id": uuid.uuid4().hex,
                "timestamp": timestamp,
                "session_id": session_id,
                "user_id": user.user_id,
                "role": user.role,
                "ip_address": self._ip_address(),
                "location": location,
                "device_id": device_id,
                "resource": resource,
                "command": command,
                "success": int(success),
                "data_mb": round(max(data_mb, 0), 3),
                "privileged": int(privileged),
                # Ground truth only. Detector must not use this feature.
                "attack_type": attack_type,
                "is_attack": int(attack_type != "normal"),
            }
        )

    def _generate_normal_session(
        self,
        user: UserProfile,
        day: datetime,
    ) -> None:
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        start_hour = np.random.normal(
            user.normal_start_hour,
            0.65,
        )

        current_time = self._hour_to_time(day, start_hour)

        device = random.choices(
            [user.primary_device, user.secondary_device],
            weights=[0.9, 0.1],
            k=1,
        )[0]

        resources = ROLES[user.role]["resources"]
        commands = ROLES[user.role]["commands"]

        self._append_event(
            user=user,
            timestamp=current_time,
            session_id=session_id,
            resource="email",
            command="login",
            location=user.home_location,
            device_id=device,
        )

        number_of_events = random.randint(8, 24)

        for _ in range(number_of_events):
            current_time += timedelta(minutes=random.randint(3, 30))

            resource = random.choice(resources)
            command = random.choice(commands)

            data_mb = 0.0

            if command in {"download", "upload"}:
                data_mb = np.random.lognormal(
                    np.log(max(user.typical_data_mb, 1)),
                    0.4,
                )

            privileged = command == "privileged_command" and user.role == "admin"

            self._append_event(
                user=user,
                timestamp=current_time,
                session_id=session_id,
                resource=resource,
                command=command,
                location=user.home_location,
                device_id=device,
                success=True,
                data_mb=data_mb,
                privileged=privileged,
            )

    def generate_normal_history(self) -> None:
        for day_offset in range(self.num_days):
            day = self.start_date + timedelta(days=day_offset)

            # Lower activity on weekends.
            attendance_probability = 0.30 if day.weekday() >= 5 else 0.92

            for user in self.users:
                if random.random() < attendance_probability:
                    self._generate_normal_session(user, day)

    def inject_legitimate_behavior_changes(self, count: int = 80) -> None:
        """
        Generate unusual but BENIGN behavior.

        These are hard negatives designed to prevent the detector
        from learning that every behavioral deviation is malicious.
        """

        for _ in range(count):
            user = random.choice(self.users)

            day = self.start_date + timedelta(days=random.randint(5, self.num_days - 1))

            scenario = random.choice(
                [
                    "late_work",
                    "business_travel",
                    "new_device",
                    "large_download",
                    "failed_passwords",
                    "temporary_project",
                ]
            )

            session_id = f"session_{uuid.uuid4().hex[:12]}"

            # ---------------------------------------------
            # Legitimate late-night work
            # ---------------------------------------------

            if scenario == "late_work":

                timestamp = self._hour_to_time(
                    day,
                    random.uniform(21.5, 23.8),
                )

                for i in range(random.randint(5, 12)):

                    self._append_event(
                        user=user,
                        timestamp=timestamp + timedelta(minutes=i * 8),
                        session_id=session_id,
                        resource=random.choice(ROLES[user.role]["resources"]),
                        command=random.choice(ROLES[user.role]["commands"]),
                        location=user.home_location,
                        device_id=user.primary_device,
                        success=True,
                        data_mb=random.uniform(0, 20),
                        attack_type="normal",
                    )

            # ---------------------------------------------
            # Legitimate international business travel
            # ---------------------------------------------

            elif scenario == "business_travel":

                location = random.choice(LOCATIONS[6:])

                timestamp = self._hour_to_time(
                    day,
                    random.uniform(8, 18),
                )

                for i in range(random.randint(6, 15)):

                    self._append_event(
                        user=user,
                        timestamp=timestamp + timedelta(minutes=i * 10),
                        session_id=session_id,
                        resource=random.choice(ROLES[user.role]["resources"]),
                        command=random.choice(ROLES[user.role]["commands"]),
                        location=location,
                        device_id=user.primary_device,
                        success=True,
                        data_mb=random.uniform(0, 25),
                        attack_type="normal",
                    )

            # ---------------------------------------------
            # Legitimate new laptop / replacement device
            # ---------------------------------------------

            elif scenario == "new_device":

                new_device = f"replacement_{uuid.uuid4().hex[:8]}"

                timestamp = self._hour_to_time(
                    day,
                    user.normal_start_hour + random.uniform(-1, 1),
                )

                for i in range(random.randint(6, 14)):

                    self._append_event(
                        user=user,
                        timestamp=timestamp + timedelta(minutes=i * 12),
                        session_id=session_id,
                        resource=random.choice(ROLES[user.role]["resources"]),
                        command=random.choice(ROLES[user.role]["commands"]),
                        location=user.home_location,
                        device_id=new_device,
                        success=True,
                        data_mb=random.uniform(0, 15),
                        attack_type="normal",
                    )

            # ---------------------------------------------
            # Legitimate large file transfer
            # ---------------------------------------------

            elif scenario == "large_download":

                timestamp = self._hour_to_time(
                    day,
                    user.normal_start_hour + random.uniform(-1, 2),
                )

                self._append_event(
                    user=user,
                    timestamp=timestamp,
                    session_id=session_id,
                    resource=random.choice(ROLES[user.role]["resources"]),
                    command="download",
                    location=user.home_location,
                    device_id=user.primary_device,
                    success=True,
                    data_mb=user.typical_data_mb * random.uniform(3, 7),
                    attack_type="normal",
                )

            # ---------------------------------------------
            # Human forgot password
            # ---------------------------------------------

            elif scenario == "failed_passwords":

                timestamp = self._hour_to_time(
                    day,
                    user.normal_start_hour + random.uniform(-1, 1),
                )

                attempts = random.randint(2, 5)

                for i in range(attempts):

                    self._append_event(
                        user=user,
                        timestamp=timestamp + timedelta(seconds=i * 20),
                        session_id=session_id,
                        resource="email",
                        command="login",
                        location=user.home_location,
                        device_id=user.primary_device,
                        success=False,
                        attack_type="normal",
                    )

                # Eventually succeeds.

                self._append_event(
                    user=user,
                    timestamp=timestamp + timedelta(seconds=(attempts + 1) * 20),
                    session_id=session_id,
                    resource="email",
                    command="login",
                    location=user.home_location,
                    device_id=user.primary_device,
                    success=True,
                    attack_type="normal",
                )

            # ---------------------------------------------
            # Legitimate temporary cross-project access
            # ---------------------------------------------

            elif scenario == "temporary_project":

                timestamp = self._hour_to_time(
                    day,
                    user.normal_start_hour + random.uniform(-1, 2),
                )

                unusual_resources = [
                    r for r in RESOURCES if r not in ROLES[user.role]["resources"]
                ]

                if not unusual_resources:
                    continue

                temporary_resource = random.choice(unusual_resources)

                for i in range(random.randint(3, 8)):

                    self._append_event(
                        user=user,
                        timestamp=timestamp + timedelta(minutes=i * 15),
                        session_id=session_id,
                        resource=temporary_resource,
                        command=random.choice(["read", "write", "download"]),
                        location=user.home_location,
                        device_id=user.primary_device,
                        success=True,
                        data_mb=random.uniform(0, 30),
                        attack_type="normal",
                    )

    def _random_attack_day(
        self,
        start_offset: int,
        end_offset: int,
    ) -> datetime:

        start_offset = max(0, start_offset)
        end_offset = min(
            self.num_days - 1,
            end_offset,
        )

        if start_offset > end_offset:
            raise ValueError("Invalid attack date window.")

        offset = random.randint(
            start_offset,
            end_offset,
        )

        return self.start_date + timedelta(days=offset)

    def _attack_windows(self) -> dict:

        train_end = int(self.num_days * 0.70)
        val_end = int(self.num_days * 0.80)

        return {
            "train": (5, train_end - 1),
            "validation": (train_end, val_end - 1),
            "test": (val_end, self.num_days - 1),
        }

    def inject_brute_force(
        self,
        count: int = 12,
        start_offset: int = 5,
        end_offset: int | None = None,
    ) -> None:

        if end_offset is None:
            end_offset = self.num_days - 1

        for _ in range(count):
            user = random.choice(self.users)

            day = self._random_attack_day(
                start_offset,
                end_offset,
            )

            timestamp = self._hour_to_time(
                day,
                random.choice([1.5, 2.5, 3.5, 22.5, 23.5]),
            )

            session_id = f"session_{uuid.uuid4().hex[:12]}"

            attacker_device = f"unknown_{uuid.uuid4().hex[:8]}"

            attempts = random.randint(12, 35)

            for i in range(attempts):
                self._append_event(
                    user=user,
                    timestamp=timestamp + timedelta(seconds=i * random.randint(5, 20)),
                    session_id=session_id,
                    resource="email",
                    command="login",
                    location=random.choice(LOCATIONS[6:]),
                    device_id=attacker_device,
                    success=False,
                    attack_type="brute_force",
                )

    def inject_impossible_travel(
        self,
        count: int = 12,
        start_offset: int = 5,
        end_offset: int | None = None,
    ) -> None:

        if end_offset is None:
            end_offset = self.num_days - 1

        for _ in range(count):
            user = random.choice(self.users)

            day = self._random_attack_day(
                start_offset,
                end_offset,
            )

            session_id = f"session_{uuid.uuid4().hex[:12]}"

            first_time = self._hour_to_time(
                day,
                user.normal_start_hour,
            )

            foreign_location = random.choice(LOCATIONS[6:])

            self._append_event(
                user=user,
                timestamp=first_time,
                session_id=session_id,
                resource="email",
                command="login",
                location=user.home_location,
                device_id=user.primary_device,
                success=True,
                attack_type="impossible_travel",
            )

            self._append_event(
                user=user,
                timestamp=first_time + timedelta(minutes=random.randint(10, 45)),
                session_id=session_id,
                resource="email",
                command="login",
                location=foreign_location,
                device_id=(f"unknown_{uuid.uuid4().hex[:8]}"),
                success=True,
                attack_type="impossible_travel",
            )

    def inject_device_spoofing(
        self,
        count: int = 12,
        start_offset: int = 5,
        end_offset: int | None = None,
    ) -> None:

        if end_offset is None:
            end_offset = self.num_days - 1

        for _ in range(count):
            user = random.choice(self.users)

            day = self._random_attack_day(
                start_offset,
                end_offset,
            )

            timestamp = self._hour_to_time(
                day,
                user.normal_start_hour + random.uniform(-1, 1),
            )

            session_id = f"session_{uuid.uuid4().hex[:12]}"

            for i in range(random.randint(4, 10)):
                self._append_event(
                    user=user,
                    timestamp=timestamp + timedelta(minutes=i * 3),
                    session_id=session_id,
                    resource=random.choice(ROLES[user.role]["resources"]),
                    command=random.choice(["login", "read", "download"]),
                    location=user.home_location,
                    device_id=(f"spoofed_{uuid.uuid4().hex[:8]}"),
                    success=True,
                    data_mb=random.uniform(0, 20),
                    attack_type="device_spoofing",
                )

    def inject_lateral_movement(
        self,
        count: int = 10,
        start_offset: int = 5,
        end_offset: int | None = None,
    ) -> None:

        if end_offset is None:
            end_offset = self.num_days - 1

        for _ in range(count):
            user = random.choice(self.users)

            day = self._random_attack_day(
                start_offset,
                end_offset,
            )

            timestamp = self._hour_to_time(
                day,
                random.uniform(0, 5),
            )

            session_id = f"session_{uuid.uuid4().hex[:12]}"

            sequence = [
                ("email", "login"),
                ("admin_console", "enumerate"),
                ("file_server", "read"),
                ("database", "query"),
                (
                    "credential_store",
                    "privileged_command",
                ),
                ("dev_server", "execute"),
            ]

            for i, (resource, command) in enumerate(sequence):
                self._append_event(
                    user=user,
                    timestamp=timestamp + timedelta(minutes=i * 2),
                    session_id=session_id,
                    resource=resource,
                    command=command,
                    location=user.home_location,
                    device_id=user.primary_device,
                    success=True,
                    privileged=(command == "privileged_command"),
                    attack_type="lateral_movement",
                )

    def inject_credential_stuffing(
        self,
        count: int = 10,
        start_offset: int = 5,
        end_offset: int | None = None,
    ) -> None:

        if end_offset is None:
            end_offset = self.num_days - 1

        for _ in range(count):

            day = self._random_attack_day(
                start_offset,
                end_offset,
            )

            location = random.choice(LOCATIONS[6:])

            attacker_device = f"bot_{uuid.uuid4().hex[:8]}"

            selected_users = random.sample(
                self.users,
                k=min(
                    random.randint(5, 12),
                    len(self.users),
                ),
            )

            base_time = self._hour_to_time(
                day,
                random.uniform(0, 5),
            )

            for index, user in enumerate(selected_users):
                session_id = f"session_{uuid.uuid4().hex[:12]}"

                self._append_event(
                    user=user,
                    timestamp=base_time + timedelta(seconds=index * 20),
                    session_id=session_id,
                    resource="email",
                    command="login",
                    location=location,
                    device_id=attacker_device,
                    success=(random.random() < 0.15),
                    attack_type=("credential_stuffing"),
                )

    def inject_low_slow_exfiltration(
        self,
        campaigns: int = 5,
        start_offset: int = 5,
        end_offset: int | None = None,
    ) -> None:

        if end_offset is None:
            end_offset = self.num_days - 1

        campaign_length = 7

        latest_start = end_offset - campaign_length + 1

        if latest_start < start_offset:
            return

        for _ in range(campaigns):
            user = random.choice(self.users)

            campaign_start = random.randint(
                start_offset,
                latest_start,
            )

            for day_offset in range(campaign_length):
                day = self.start_date + timedelta(days=campaign_start + day_offset)

                timestamp = self._hour_to_time(
                    day,
                    user.normal_start_hour + random.uniform(2, 5),
                )

                session_id = f"session_{uuid.uuid4().hex[:12]}"

                transfer = user.typical_data_mb * (1.2 + day_offset * 0.35)

                self._append_event(
                    user=user,
                    timestamp=timestamp,
                    session_id=session_id,
                    resource="file_server",
                    command="download",
                    location=user.home_location,
                    device_id=user.primary_device,
                    success=True,
                    data_mb=transfer,
                    attack_type=("low_slow_exfiltration"),
                )

    def inject_insider_drift(
        self,
        campaigns: int = 5,
        start_offset: int = 5,
        end_offset: int | None = None,
    ) -> None:

        if end_offset is None:
            end_offset = self.num_days - 1

        campaign_length = 6

        latest_start = end_offset - campaign_length + 1

        if latest_start < start_offset:
            return

        for _ in range(campaigns):
            user = random.choice(self.users)

            campaign_start = random.randint(
                start_offset,
                latest_start,
            )

            unusual_resources = [
                r for r in RESOURCES if r not in ROLES[user.role]["resources"]
            ]

            if not unusual_resources:
                continue

            for day_offset in range(campaign_length):
                day = self.start_date + timedelta(days=campaign_start + day_offset)

                timestamp = self._hour_to_time(
                    day,
                    user.normal_start_hour + 5 + day_offset * 0.15,
                )

                session_id = f"session_{uuid.uuid4().hex[:12]}"

                self._append_event(
                    user=user,
                    timestamp=timestamp,
                    session_id=session_id,
                    resource=random.choice(unusual_resources),
                    command=random.choice(
                        [
                            "read",
                            "download",
                            "enumerate",
                        ]
                    ),
                    location=user.home_location,
                    device_id=user.primary_device,
                    success=True,
                    data_mb=(user.typical_data_mb * (1 + 0.25 * day_offset)),
                    attack_type="insider_drift",
                )

    def generate(self) -> pd.DataFrame:
        # ==================================================
        # 1. BACKGROUND ENTERPRISE ACTIVITY
        # ==================================================

        self.generate_normal_history()

        # Hard benign anomalies.
        self.inject_legitimate_behavior_changes(count=100)

        # ==================================================
        # 2. TEMPORAL WINDOWS
        # ==================================================

        windows = self._attack_windows()

        train_start, train_end = windows["train"]
        val_start, val_end = windows["validation"]
        test_start, test_end = windows["test"]

        # ==================================================
        # 3. TRAIN ATTACKS
        # ==================================================

        self.inject_brute_force(
            count=18,
            start_offset=train_start,
            end_offset=train_end,
        )

        self.inject_credential_stuffing(
            count=8,
            start_offset=train_start,
            end_offset=train_end,
        )

        self.inject_impossible_travel(
            count=18,
            start_offset=train_start,
            end_offset=train_end,
        )

        self.inject_device_spoofing(
            count=18,
            start_offset=train_start,
            end_offset=train_end,
        )

        self.inject_lateral_movement(
            count=18,
            start_offset=train_start,
            end_offset=train_end,
        )

        self.inject_low_slow_exfiltration(
            campaigns=3,
            start_offset=train_start,
            end_offset=train_end,
        )

        self.inject_insider_drift(
            campaigns=3,
            start_offset=train_start,
            end_offset=train_end,
        )

        # ==================================================
        # 4. VALIDATION ATTACKS
        # ==================================================

        self.inject_brute_force(
            count=6,
            start_offset=val_start,
            end_offset=val_end,
        )

        self.inject_credential_stuffing(
            count=2,
            start_offset=val_start,
            end_offset=val_end,
        )

        self.inject_impossible_travel(
            count=6,
            start_offset=val_start,
            end_offset=val_end,
        )

        self.inject_device_spoofing(
            count=6,
            start_offset=val_start,
            end_offset=val_end,
        )

        self.inject_lateral_movement(
            count=6,
            start_offset=val_start,
            end_offset=val_end,
        )

        # Long-running campaigns are not forced into the
        # short validation window.

        # ==================================================
        # 5. TEST ATTACKS
        # ==================================================

        self.inject_brute_force(
            count=10,
            start_offset=test_start,
            end_offset=test_end,
        )

        self.inject_credential_stuffing(
            count=3,
            start_offset=test_start,
            end_offset=test_end,
        )

        self.inject_impossible_travel(
            count=10,
            start_offset=test_start,
            end_offset=test_end,
        )

        self.inject_device_spoofing(
            count=10,
            start_offset=test_start,
            end_offset=test_end,
        )

        self.inject_lateral_movement(
            count=10,
            start_offset=test_start,
            end_offset=test_end,
        )

        self.inject_low_slow_exfiltration(
            campaigns=2,
            start_offset=test_start,
            end_offset=test_end,
        )

        self.inject_insider_drift(
            campaigns=1,
            start_offset=test_start,
            end_offset=test_end,
        )

        # ==================================================
        # 6. FINAL DATASET
        # ==================================================

        df = pd.DataFrame(self.events)

        df["timestamp"] = pd.to_datetime(df["timestamp"])

        df = df.sort_values("timestamp").reset_index(drop=True)

        return df


def save_dataset(df: pd.DataFrame) -> Path:
    project_root = Path(__file__).resolve().parents[1]

    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "security_events.csv"

    df.to_csv(output_path, index=False)

    return output_path


if __name__ == "__main__":
    generator = SecurityLogGenerator(
        num_users=80,
        num_days=45,
    )

    dataframe = generator.generate()

    path = save_dataset(dataframe)

    print("\nSentinelTwin Synthetic Dataset")
    print("=" * 45)
    print(f"Events: {len(dataframe):,}")
    print(f"Users: {dataframe['user_id'].nunique()}")
    print(f"Sessions: {dataframe['session_id'].nunique()}")
    print(f"Attack events: {dataframe['is_attack'].sum():,}")
    print(f"Attack rate: " f"{dataframe['is_attack'].mean() * 100:.2f}%")

    print("\nAttack distribution:")
    print(dataframe["attack_type"].value_counts())

    print(f"\nSaved to: {path}")
