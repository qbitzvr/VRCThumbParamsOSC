﻿using System.Collections.Generic;

namespace Configurator
{
    public class Action
    {
        public string name { get; set; }
        public string type { get; set; }
        public object osc_parameter { get; set; }
        public object enabled { get; set; }
        public object floating { get; set; }
        public object timestamp { get; set; }
        public object last_value { get; set; }
    }

    public class ControllerType
    {
        public bool enabled { get; set; }
        public int last_value { get; set; }
        public int timestamp { get; set; }
    }

    public class DefaultBinding
    {
        public string controller_type { get; set; }
        public string binding_url { get; set; }
    }

    public class Config
    {
        public string IP { get; set; }
        public int Port { get; set; }
        public int PollingRate { get; set; }
        public int StickMoveTolerance { get; set; }
        public ControllerType ControllerType { get; set; }
        public bool LeftThumb { get; set; }
        public bool RightThumb { get; set; }
        public bool LeftABButtons { get; set; }
        public bool RightABButtons { get; set; }
        public List<DefaultBinding> default_bindings { get; set; }
        public List<Action> actions { get; set; }
    }

}