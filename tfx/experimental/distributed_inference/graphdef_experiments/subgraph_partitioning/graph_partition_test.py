# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for Graph Partitioning."""

import os
import tensorflow as tf

import graph_partition


class RelationTest(tf.test.TestCase):
  """Tests for Relation."""
  def test_layers(self):
    """Construct an example and validate the layers."""
    remote_op_relations = {'a1': [], 'a2': [], 'b1': ['a1'],
                           'b2': ['a1', 'a2'], 'c1': ['b1'],
                           'c2': ['b1', 'a1', 'b2', 'a2']}
    relations = graph_partition.Relations(remote_op_relations)

    self.assertFalse(relations.check_if_finished())
    self.assertFalse(relations.check_if_finished())

    self.assertEqual(relations.get_next_layer(), {'a1', 'a2'})
    self.assertFalse(relations.check_if_finished())
    self.assertEqual(relations.get_next_layer(), {'b1', 'b2'})
    self.assertFalse(relations.check_if_finished())
    self.assertEqual(relations.get_next_layer(), {'c1', 'c2'})

    self.assertTrue(relations.check_if_finished())
    self.assertTrue(relations.check_if_finished())


def _get_path(folder_name, file_name):
  return os.path.join(os.path.join(os.path.dirname(__file__), folder_name),
                      file_name)

op_to_filename = {'main': _get_path('complex_graphdefs', 'main_graph.pb'),
                  'remote_op_a': _get_path('complex_graphdefs', 'graph_a.pb'),
                  'remote_op_b': _get_path('complex_graphdefs', 'graph_b.pb'),
                 }
op_to_outputs = {'main': ['AddN_1'],
                 'remote_op_b': ['Add_1'],
                 'remote_op_a': ['embedding_lookup/Identity'],
                }

op_to_graph_def = graph_partition.get_op_to_graph_def(op_to_filename)
op_to_execution_specs = graph_partition.partition_all_graphs(op_to_graph_def,
                                                             op_to_outputs)


class PartitionTest(tf.test.TestCase):
  """Tests for graph partitioning."""

  def test_op_names(self):
    """Validate op names."""
    op_keys = set(op_to_outputs.keys())
    op_current_keys = set(op_to_execution_specs.keys())
    self.assertEqual(op_keys, op_current_keys)


  def test_subgraph_import_validity(self):
    """Try to import subgraphs and see if they're valid."""
    for execution_specs in op_to_execution_specs.values():
      for execution_spec in execution_specs:
        if not execution_spec['is_remote_op']:
          graph = tf.Graph()
          with graph.as_default():
            tf.import_graph_def(execution_spec['subgraph'])


  def test_subgraph_specs(self):
    """Validate a subgraph spec."""
    for execution_specs in op_to_execution_specs.values():
      for spec in execution_specs:
        if not spec['is_remote_op']:
          all_nodes = self._get_node_names_from_subgraph(spec['subgraph'])

          self.assertTrue(spec['outputs'].issubset(spec['body_nodes']))
          self.assertEqual(all_nodes, spec['body_nodes'].union(spec['inputs']))

          for input_name in spec['inputs']:
            self.assertNotIn(input_name, spec['body_nodes'])

          for node_from_other_layer in spec['nodes_from_other_layers']:
            self.assertNotIn(node_from_other_layer, spec['body_nodes'])


  def _get_node_names_from_subgraph(self, subgraph):
    node_names = {node.name for node in subgraph.node}
    return node_names


  def test_remote_op_specs(self):
    """Validate a remote op spec."""
    for execution_specs in op_to_execution_specs.values():
      for spec in execution_specs:
        if spec['is_remote_op']:
          self.assertIsNone(spec['subgraph'])
          self.assertLen(spec['outputs'], 1)
          self.assertLen(spec['body_nodes'], 1)


if __name__ == '__main__':
  tf.test.main()
  