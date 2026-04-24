
    <link name="propeller_link">
      <pose relative_to="base_link">0 0.17 0 0 1.5708 0</pose>
      <inertial>
        <mass>0</mass>
      </inertial>

      <visual name="visual">
        <geometry>
          <cylinder>
            <radius>0.03</radius>
            <length>0.02</length>
          </cylinder>
        </geometry>
      </visual>
    </link>

    <joint name="propeller_joint" type="revolute">
      <parent>base_link</parent>
      <child>propeller_link</child>
      <axis>
        <xyz>1 0 0</xyz>
        <limit>
          <lower>-1e16</lower>
          <upper>1e16</upper>
        </limit>
      </axis>
    </joint>

    <plugin filename="gz-sim-thruster-system"
            name="gz::sim::systems::Thruster">
      <namespace>rov</namespace>
      <joint_name>propeller_joint</joint_name>
      <thrust_coefficient>0.004422</thrust_coefficient>
      <fluid_density>1000</fluid_density>
      <propeller_diameter>0.1</propeller_diameter>
      <velocity_control>false</velocity_control>
      <max_thrust_cmd>30</max_thrust_cmd>
      <min_thrust_cmd>-30</min_thrust_cmd>
    </plugin>